from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from scipy.stats import chi2_contingency
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier, AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
                             classification_report, RocCurveDisplay)
from sklearn.model_selection import train_test_split, GridSearchCV, cross_validate, validation_curve, RandomizedSearchCV
from sklearn.neighbors import KNeighborsClassifier, LocalOutlierFactor
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder, RobustScaler, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, export_graphviz, export_text
from xgboost import XGBClassifier
import graphviz
import joblib
import matplotlib.pyplot as plt
import missingno as msno
import numpy as np
import pandas as pd
import seaborn as sns
import warnings
from collections import Counter
from sklearn.datasets import make_classification
from imblearn.over_sampling import SMOTE
from matplotlib import pyplot
from numpy import where
from sklearn.metrics import classification_report
from sklearn.impute import KNNImputer
from statsmodels.stats.outliers_influence import variance_inflation_factor

warnings.simplefilter(action="ignore")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 170)
pd.set_option('display.max_rows', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)

# Fonksiyonlarımız:
def grab_col_names(dataframe, cat_th=9, car_th=20):
    #cat_cols, cat_but_car
    cat_cols = [col for col in dataframe.columns if dataframe[col].dtypes == "O"]
    num_but_cat = [col for col in dataframe.columns if dataframe[col].nunique() < cat_th and
                   dataframe[col].dtypes != "O"]
    cat_but_car = [col for col in dataframe.columns if dataframe[col].nunique() > car_th and
                   dataframe[col].dtypes == "O"]
    cat_cols = cat_cols + num_but_cat
    cat_cols = [col for col in cat_cols if col not in cat_but_car]

    #num_cols
    num_cols = [col for col in dataframe.columns if dataframe[col].dtypes != "O"]
    num_cols = [col for col in num_cols if col not in num_but_cat]

    print(f"Observations: {dataframe.shape[0]}")
    print(f"Variables: {dataframe.shape[1]}")
    print(f"cat_cols: {len(cat_cols)}")
    print(f"num_cols: {len(num_cols)}")
    print(f"cat_but_car: {len(cat_but_car)}")
    print(f"num_but_car: {len(num_but_cat)}")
    return cat_cols, num_cols, cat_but_car

def outlier_thresholds(dataframe, col_name, q1=0.05, q3=0.95):
    quartile1 = dataframe[col_name].quantile(q1)
    quartile3 = dataframe[col_name].quantile(q3)
    interquantile_range = quartile3 - quartile1
    up_limit = quartile3 + 1.5 * interquantile_range
    low_limit = quartile1 - 1.5 * interquantile_range
    return low_limit, up_limit

def check_outlier(dataframe, col_name):
    low_limit, up_limit = outlier_thresholds(dataframe, col_name)
    if dataframe[(dataframe[col_name] > up_limit) | (dataframe[col_name] < low_limit)].any(axis=None):
        return True
    else:
        return False

def grab_outliers(dataframe, col_name, index=False):
    low, up = outlier_thresholds(dataframe, col_name)
    print(dataframe[((dataframe[col_name] < low) | (dataframe[col_name] > up))].shape[0])
    # if dataframe[((dataframe[col_name] < low) | (dataframe[col_name] > up))].shape[0] > 10:
    #     print(dataframe[((dataframe[col_name] < low) | (dataframe[col_name] > up))].head())
    # else:
    #     print(dataframe[((dataframe[col_name] < low) | (dataframe[col_name] > up))])

    if index:
        outlier_index = dataframe[((dataframe[col_name] < low) | (dataframe[col_name] > up))].index
        return outlier_index

def replace_with_thresholds(dataframe, variable):
    low_limit, up_limit = outlier_thresholds(dataframe, variable)
    dataframe.loc[(dataframe[variable] < low_limit), variable] = low_limit
    dataframe.loc[(dataframe[variable] > up_limit), variable] = up_limit

def cat_summary(dataframe, col_name, plot=False):
    print(pd.DataFrame({col_name: dataframe[col_name].value_counts(),
                        "Ratio": 100 * dataframe[col_name].value_counts() / len(dataframe)}))
    print("##########################################")
    if plot:
        sns.countplot(x=dataframe[col_name], data=dataframe)
        plt.show(block=True)

def num_summary(dataframe, numerical_col, plot=False):
    quantiles = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99]
    print(dataframe[numerical_col].describe(quantiles).T)

    if plot:
        dataframe[numerical_col].hist(bins=20)
        plt.xlabel(numerical_col)
        plt.title(numerical_col)
        plt.show(block=True)

def one_hot_encoder(dataframe, categorical_cols, drop_first=True):
    dataframe = pd.get_dummies(dataframe, columns=categorical_cols, drop_first=drop_first, dtype=int)
    return dataframe

def combine_categories(df, cat_col1, cat_col2, new_col_name):
    df[new_col_name] = df[cat_col1].astype(str) + '_' + df[cat_col2].astype(str)

df = pd.read_csv("BankChurners.csv")

df.drop([
    "Naive_Bayes_Classifier_Attrition_Flag_Card_Category_Contacts_Count_12_mon_Dependent_count_Education_Level_Months_Inactive_12_mon_1",
    "Naive_Bayes_Classifier_Attrition_Flag_Card_Category_Contacts_Count_12_mon_Dependent_count_Education_Level_Months_Inactive_12_mon_2"],
    inplace=True, axis=1)

# Bağımlı değişkenimizin ismini target yapalım ve 1, 0 atayalım:
df.rename(columns={"Attrition_Flag": "Target"}, inplace=True)
df["Target"] = df.apply(lambda x: 0 if (x["Target"] == "Existing Customer") else 1, axis=1)

# ID kolonunda duplicate bakıp, sonra bu değişkeni silme
df["CLIENTNUM"].nunique()  # 10127 - yani duplicate yok id'de
df.drop("CLIENTNUM", axis=1, inplace=True)

cat_cols, num_cols, cat_but_car = grab_col_names(df)

# Outlier temizleme (IQR ve LOF):
# IQR
for col in num_cols:
    print(col)
    grab_outliers(df, col)

for col in num_cols:
    replace_with_thresholds(df, col)

# LOF
clf = LocalOutlierFactor(n_neighbors=20)
clf.fit_predict(df[num_cols])

df_scores = clf.negative_outlier_factor_

scores = pd.DataFrame(np.sort(df_scores))
scores.plot(stacked=True, xlim=[0, 100], style='.-')
plt.show()

th = np.sort(df_scores)[25]

df[df_scores < th].drop(axis=0, labels=df[df_scores < th].index)

# Missing values
cols_with_unknown = ['Income_Category', "Education_Level"]
for col in cols_with_unknown:
    df[col] = df[col].apply(lambda x: np.nan if x == 'Unknown' else x)


# Yeni değişkenler üretme:
labels = ['Young', 'Middle_Aged', 'Senior']
bins = [25, 35, 55, 74]
df['Customer_Age_Category'] = pd.cut(df['Customer_Age'], bins=bins, labels=labels)

df["MonetaryScore"] = pd.qcut(df["Total_Trans_Amt"], 5, labels=[1, 2, 3, 4, 5])
df["FrequencyScore"] = pd.qcut(df["Total_Trans_Ct"], 5, labels=[1, 2, 3, 4, 5])

combine_categories(df, 'Customer_Age_Category', 'Marital_Status', 'Age_&_Marital')
combine_categories(df, 'Gender', 'Customer_Age_Category', 'Gender_&_Age')
combine_categories(df, "Card_Category", "Customer_Age_Category", "Card_&_Age")
combine_categories(df, "Gender", "FrequencyScore", "Gender_&_Frequency")
combine_categories(df, "Gender", "MonetaryScore", "Gender_&_Monetary")


df['Total_Amt_Increased'] = np.where((df['Total_Amt_Chng_Q4_Q1'] > 0) & (df['Total_Amt_Chng_Q4_Q1'] < 1), 0, 1)
df['Total_Ct_Increased'] = np.where((df['Total_Ct_Chng_Q4_Q1'] > 0) & (df['Total_Ct_Chng_Q4_Q1'] < 1), 0, 1)

cat_cols, num_cols, cat_but_car = grab_col_names(df)


# Encoding:

# Rare encoding:
df["Card_Category"] = df["Card_Category"].apply(lambda x: "Gold_Platinum" if x == "Platinum" or x == "Gold" else x)
df["Months_Inactive_12_mon"] = df["Months_Inactive_12_mon"].apply(lambda x: 1 if x == 0 else x)
df["Card_&_Age"] = df["Card_&_Age"].apply(lambda x: "Rare" if df["Card_&_Age"].value_counts()[x] < 30 else x)

# Ordinal encoding:
def ordinal_encoder(dataframe, col):
    edu_cats = ['Uneducated', 'High School', 'College', 'Graduate', 'Post-Graduate', 'Doctorate', np.nan]
    income_cats = ['Less than $40K', '$40K - $60K', '$60K - $80K', '$80K - $120K', '$120K +', np.nan]
    customer_age_cat = [ 'Young','Middle_Aged', 'Senior']

    if col is "Education_Level":
        col_cats = edu_cats
    if col is "Income_Category":
        col_cats = income_cats
    if col is "Customer_Age_Category":
        col_cats = customer_age_cat

    ordinal_encoder = OrdinalEncoder(categories=[col_cats])  # burada direkt int alamıyorum çünkü NaN'lar mevcut.
    df[col] = ordinal_encoder.fit_transform(df[[col]])

    print(df[col].head(20))
    return df


df = ordinal_encoder(df, "Education_Level")
df = ordinal_encoder(df, "Income_Category")
df = ordinal_encoder(df, "Customer_Age_Category")

# One-hot encoding:
df = one_hot_encoder(df, ["Gender", "Marital_Status", "Card_Category",
                          "Age_&_Marital", "Gender_&_Age", "Card_&_Age", "Gender_&_Frequency", "Gender_&_Monetary"], drop_first=True)




# Nan doldurma:
imputer = KNNImputer(n_neighbors=10)
df = pd.DataFrame(imputer.fit_transform(df), columns=df.columns)

df["Education_Level"] = df["Education_Level"].round().astype(int)
df["Income_Category"] = df["Income_Category"].round().astype(int)


cat_cols, num_cols, cat_but_car = grab_col_names(df)

# Değişken tipi dönüştürme:
for col in df.columns:
    if df[col].dtype == 'float64':  # Sadece float sütunları kontrol edelim
        if (df[col] % 1 == 000).all():  # Tüm değerlerin virgülden sonrası 0 mı kontrol edelim
            df[col] = df[col].astype(int)

cat_cols, num_cols, cat_but_car = grab_col_names(df)

# Feature scaling (robust):
rs = RobustScaler()
df[num_cols] = rs.fit_transform(df[num_cols])


# Korelasyon Heatmap:

def high_coralated_cols(dataframe, plot=False, corr_th=0.90):
    corr = dataframe[num_cols].corr()
    cor_matrix = corr.abs()
    upper_triangle_matrix = cor_matrix.where(np.triu(np.ones(cor_matrix.shape), k=1).astype(bool))
    drop_list = [col for col in upper_triangle_matrix if any(upper_triangle_matrix[col] > corr_th)]
    if plot:
        sns.set(rc={'figure.figsize': (12, 12)})
        sns.heatmap(corr, cmap='RdBu', annot= True)
        plt.show()
    return drop_list


drop_list = high_coralated_cols(df, plot=True)

df.drop(columns=drop_list, inplace=True, axis=1)


cat_cols, num_cols, cat_but_car = grab_col_names(df)
# Multicollinearity test:
def calculate_vif(data):
    vif_data = pd.DataFrame()
    vif_data["Feature"] = data.columns
    vif_data["VIF"] = [variance_inflation_factor(data.values, i) for i in range(len(data.columns))]
    return vif_data


all_independent_variables = df[num_cols]
vif_results = calculate_vif(all_independent_variables)
print(vif_results)

# Model:
y = df["Target"]
X = df.drop(["Target"], axis=1)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

def model_metrics(X_train, y_train, X_test, y_test):
    print("Base Models....")
    classifiers = [('LR', LogisticRegression()),
                   ('KNN', KNeighborsClassifier()),
                   ("SVC", SVC()),
                   ("CART", DecisionTreeClassifier()),
                   ("RF", RandomForestClassifier()),
                   ('Adaboost', AdaBoostClassifier()),
                   ('GBM', GradientBoostingClassifier()),
                   ('XGBoost', XGBClassifier(use_label_encoder=False, eval_metric='logloss')),
                   ('LightGBM', LGBMClassifier()),
                   ('CatBoost', CatBoostClassifier(verbose=False))
                   ]

    for name, classifier in classifiers:
        model = classifier.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Classification Report
        report = classification_report(y_test, y_pred)
        print(f"Classification Report for {name}:")
        print(report)

model_metrics(X_train, y_train, X_test, y_test)

# Hiperparametre Optimizasyonu ve Model:

rf_params = {"max_depth": [5, 10, 15, None],
             #"max_features": [2, 4, 8, 16, 30],
             "min_samples_split": [2, 5, 10],
             "n_estimators": [50, 100, 200, 300]}

xgboost_params = {"learning_rate": [0.01, 0.05, 0.1, 0.5],
                  "max_depth": [3, 5, 7, 10],
                  "n_estimators": [50, 100, 200, 300]}

lightgbm_params = {"learning_rate": [0.01, 0.05, 0.1, 0.5],
                   "n_estimators": [50, 100, 200, 300],
                   "max_depth": [3, 5, 7, 10]}

gbm_params = {"learning_rate": [0.01, 0.1, 0.5, 1],
              "n_estimators": [50, 100, 200, 300],
              "max_depth": [3, 5, 7, 10],
              "subsample": [0.5, 0.75, 1.0]}

catboost_params = {"learning_rate": [0.01, 0.05, 0.1, 0.5],
                   "depth": [3, 5, 7, 10],
                   "iterations": [50, 100, 200, 300],
                   "subsample": [0.5, 0.75, 1.0]}

adaboost_params = { "n_estimators": [50, 100, 200, 300],
                    "learning_rate": [0.01, 0.05, 0.1, 0.5],
                    "base_estimator__max_depth": [1, 2, 3, 4],
                    "random_state": [None, 42]}

classifiers = ([("RF", RandomForestClassifier(), rf_params),
                ('XGBoost', XGBClassifier(use_label_encoder=False, eval_metric='logloss'), xgboost_params),
                ('LightGBM', LGBMClassifier(force_col_wise=True), lightgbm_params),
                ('GBM', GradientBoostingClassifier(), gbm_params),
                ('CatBoost', CatBoostClassifier(verbose=False), catboost_params),
                ('AdaBoost', CatBoostClassifier(), adaboost_params),
                ])


def hyperparameter_optimization(X_train, y_train, X_test, y_test, cv=3, scoring="roc_auc"):
    print("Hyperparameter Optimization....")
    best_models = {}
    for name, classifier, params in classifiers:
        print(f"########## {name} ##########")
        cv_results = cross_validate(classifier, X_train, y_train, cv=cv, scoring=scoring)
        print(f"{scoring} (Before): {round(cv_results['test_score'].mean(), 4)}")

        gs_best = GridSearchCV(classifier, params, cv=cv, n_jobs=-1, verbose=False).fit(X_train, y_train)
        final_model = classifier.set_params(**gs_best.best_params_)

        cv_results = cross_validate(final_model, X_train, y_train, cv=cv, scoring=scoring)
        print(f"{scoring} (After): {round(cv_results['test_score'].mean(), 4)}")
        print(f"{name} best params: {gs_best.best_params_}")

        # Test verileri üzerinde modelin performansını değerlendir
        final_model.fit(X_train, y_train)
        y_pred = final_model.predict(X_test)
        report = classification_report(y_test, y_pred)
        print(f"{name} classification report:\n{report}\n")

        best_models[name] = final_model

    return best_models

hyperparameter_optimization(X_train, y_train, X_test, y_test)
