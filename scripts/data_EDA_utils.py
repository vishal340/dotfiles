# Databricks notebook source
from pyspark.sql.functions import count, when, isnan, col, desc, udf, round, floor
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler, Imputer
from pyspark.ml import Pipeline
from pyspark.ml.classification import DecisionTreeClassifier, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator, BinaryClassificationEvaluator
from pyspark.sql.window import Window
from pyspark.sql.functions import monotonically_increasing_id,row_number, lit
import pyspark.sql.functions as F
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import PowerTransformer
import pandas as pd
import numpy as np
from synapse.ml.lightgbm import LightGBMClassifier
from scipy.stats.contingency import association
from pyspark.ml.feature import PCA
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
import mlflow
import mlflow.spark
from pyspark.sql.types import DoubleType
from pyspark.sql.functions import sum
from pyspark.sql import Window

from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from pyspark.sql.functions import explode
import scipy.stats
from scipy import stats
from scipy.stats import pointbiserialr

# COMMAND ----------

def get_fill_rate_lt_x(df,attr_cols,limit):
  count=df.count()
  df_fill_rates=df.select([F.round(((count-(F.count(F.when((F.trim(F.col(c))=="") | (F.isnan(c) | F.col(c).isNull()), c))))/count)*100,2).alias(c) for c in attr_cols])
  display(df_fill_rates)
  attr_lt_x_fiil_rate = [c for c in df_fill_rates.columns if df_fill_rates.select(F.col(c)).first()[0] < limit]
  
  return attr_lt_x_fiil_rate

# COMMAND ----------

def get_attr_wt_0_cnt_gt_x(df,attr_list,limit):
  df_count = df.count()
  df_fill_0 = df.select([F.round((((F.count(F.when((F.col(c)==0), c))))/df_count)*100,2).alias(c) for c in attr_list])
  display(df_fill_0)
  
  attr_gt_x = [c for c in df_fill_0.columns if df_fill_0.select(F.col(c)).first()[0] > limit]
  #print(attr_gt_x)
  
  return attr_gt_x

# COMMAND ----------

def get_attr_wt_same_value_int(df,attr_list):
  attr_same_value = [c for c in attr_list if df.select(max(F.col(c))).first()[0] == df.select(min(F.col(c))).first()[0]]
  
  return attr_same_value

# COMMAND ----------

def get_attr_wt_same_value(df,attr_list):

  count=df.count()
  
  df_fill_rates=df.select([F.round(((count-(F.count(F.when((F.trim(F.col(c))=="") | (F.isnan(c) | F.col(c).isNull()), c))))/count)*100,2).alias(c) for c in attr_list])
  
  ignore_list = [c for c in df_fill_rates.columns if df_fill_rates.select(F.col(c)).first()[0] == 0]

  attr_list1 = [x for x in attr_list if x not in ignore_list]

  attr_same_value = [c for c in attr_list1 if df.na.drop(subset=[c]).agg(F.countDistinct(c)).first()[0] == 1]

  return attr_same_value

# COMMAND ----------

def get_binary_attr_list(df,attr_list):

  count=df.count()
  
  df_fill_rates=df.select([F.round(((count-(F.count(F.when((F.trim(F.col(c))=="") | (F.isnan(c) | F.col(c).isNull()), c))))/count)*100,2).alias(c) for c in attr_list])
  
  ignore_list = [c for c in df_fill_rates.columns if df_fill_rates.select(F.col(c)).first()[0] == 0]

  attr_list1 = [x for x in attr_list if x not in ignore_list]

  binary_attr_list = [c for c in attr_list1 if df.na.drop(subset=[c]).agg(F.countDistinct(c)).first()[0] == 2]

  return binary_attr_list

# COMMAND ----------

def outlier_detection_iqr(df, attr_list, factor):
    for column in attr_list:
        # Calculate Q1, Q3, and IQR
        quantiles = df.approxQuantile(column, [0.25, 0.75], 0.01)
        if len(quantiles) == 2:
          q1, q3 = quantiles[0], quantiles[1]
          iqr = q3 - q1

          # Define the upper and lower bounds for outliers
          lower_bound = q1 - factor * iqr
          upper_bound = q3 + factor * iqr

          df = df.withColumn(column+'_outlier', when((col(column) >= lower_bound) & (col(column) <= upper_bound), lit("0")).otherwise(lit("1"))) 
          #display(df) 

    return df

# COMMAND ----------

def get_outlier_attr_gt_limit(df,attr_list,limit):
  df_count = df.count()
  df_outlier_perc = df.select([F.round((((F.count(F.when((F.trim(F.col(c+'_outlier'))==1), c))))/df_count)*100,2).alias(c) for c in attr_list])
  display(df_outlier_perc)
  
  attr_less_x = [c for c in df_outlier_perc.columns if df_outlier_perc.select(F.col(c)).first()[0] > limit]
  #print(attr_less_x)
  
  return attr_less_x

# COMMAND ----------

def outlier_removal_iqr(df, attr_list, factor):
    for column in attr_list:
        # Calculate Q1, Q3, and IQR
        quantiles = df.approxQuantile(column, [0.25, 0.75], 0.01)
        if len(quantiles) == 2:
          q1, q3 = quantiles[0], quantiles[1]
          iqr = q3 - q1

          # Define the upper and lower bounds for outliers
          lower_bound = q1 - factor * iqr
          upper_bound = q3 + factor * iqr

          # Filter outliers and update the DataFrame
          df = df.filter((col(column) >= lower_bound) & (col(column) <= upper_bound))

    return df

# COMMAND ----------

def outlier_removal_iqr_null_imputation(df, attr_list, factor):
  df = num_imputation(df,attr_list)
  
  for column in attr_list:  
        # Calculate Q1, Q3, and IQR
    quantiles = df.approxQuantile(column, [0.25, 0.75], 0.01)
    if len(quantiles) == 2:
      q1, q3 = quantiles[0], quantiles[1]
      iqr = q3 - q1

          # Define the upper and lower bounds for outliers
      lower_bound = q1 - factor * iqr
      upper_bound = q3 + factor * iqr

      # Filter outliers and update the DataFrame
      df = df.filter(((col(column) >= lower_bound) & (col(column) <= upper_bound)))
  return df

# COMMAND ----------

def outlier_imputation_median(df, attr_list, factor):
  df = num_imputation(df,attr_list)
  
  for column in attr_list:  
        # Calculate Q1, Q3, and IQR
    quantiles = df.approxQuantile(column, [0.25, 0.75], 0.01)
    if len(quantiles) == 2:
      q1, q3 = quantiles[0], quantiles[1]
      iqr = q3 - q1

          # Define the upper and lower bounds for outliers
      lower_bound = q1 - factor * iqr
      upper_bound = q3 + factor * iqr

      df = df.withColumn(column, when(((col(column) < lower_bound) & (col(column) > upper_bound)),lit(None)).otherwise(col(column)))
  
  df = num_imputation(df,attr_list)

  return df

# COMMAND ----------

def boxplot_analysis(df,attr_list):
  partition_cols = 2
  partition_rows = 15
  df = df.toPandas()

  fig = plt.figure(figsize=(30,40))

  for i, col in enumerate(attr_list):    
      ax=fig.add_subplot(partition_rows,partition_cols, i+1)    
      sns.boxplot(x=df[col], ax=ax)
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def histplot_analysis(df,attr_list):
  partition_cols = 2
  partition_rows = 15
  df = df.toPandas()

  fig = plt.figure(figsize= (30,40))
  
  for i, col in enumerate(attr_list):    
      ax=fig.add_subplot(partition_rows,partition_cols, i+1)    
      sns.histplot(x=df[col], ax=ax)
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def barplot_analysis(df,attr_list):
  partition_cols = 2
  partition_rows = 15
  df = df.toPandas()

  fig = plt.figure(figsize= (30,40))
  
  for i, col in enumerate(attr_list):    
      ax=fig.add_subplot(partition_rows,partition_cols, i+1)    
      sns.barplot(x=df[col], ax=ax)
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def plot_correlation(df,attr_list):
  df_pd = df.select(*attr_list).toPandas()
  fig=plt.figure(figsize=(30,12))
  corrmat=df_pd.corr()
  sns.heatmap(corrmat,annot=True)
  plt.show()

# COMMAND ----------

def get_skewness(df, attr_list):
  df_pd = df.select(*attr_list).toPandas()

  skew_pd_df = df_pd.skew(axis = 0, skipna = True)
  skew_df = spark.createDataFrame(skew_pd_df.to_frame().transpose())
  display(skew_df)

  attr_l_skewed = [c for c in skew_df.columns if skew_df.select(F.col(c)).first()[0] > 0]
  attr_r_skewed = [c for c in skew_df.columns if skew_df.select(F.col(c)).first()[0] < 0]
  attr_normal_dist = [c for c in skew_df.columns if skew_df.select(F.col(c)).first()[0] == 0]

  return attr_l_skewed, attr_r_skewed, attr_normal_dist

# COMMAND ----------

def get_kurtosis_analysis(df, attr_list):
  df_pd = df.select(*attr_list).toPandas()

  kurt_pd_df = df_pd.kurtosis(axis = 0, skipna = True)
  kurt_df = spark.createDataFrame(kurt_pd_df.to_frame().transpose())
  display(kurt_df)

  attr_leptokurtic = [c for c in kurt_df.columns if kurt_df.select(F.col(c)).first()[0] > 3]
  attr_playkurtic = [c for c in kurt_df.columns if kurt_df.select(F.col(c)).first()[0] < 3]
  attr_kurt_normal_dist = [c for c in kurt_df.columns if kurt_df.select(F.col(c)).first()[0] == 3]

  return attr_leptokurtic, attr_playkurtic, attr_kurt_normal_dist

# COMMAND ----------

def pie_chart_analysis(df,attr_list):
  partition_cols = 4
  partition_rows = 10
  df = df.toPandas()

  fig = plt.figure(figsize=(40,80))

  for i, col in enumerate(attr_list):  
      ax=fig.add_subplot(partition_rows,partition_cols, i+1) 
      df.groupby(col).size().plot(kind='pie', legend=True,autopct="%.1f%%",fontsize=24)
      plt.title(col, fontsize=24)   
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------


def pie_chart_analysis_wo_legend(df,attr_list):
  partition_cols = 4
  partition_rows = 10
  df = df.toPandas()

  fig = plt.figure(figsize=(40,80))

  for i, col in enumerate(attr_list):  
      ax=fig.add_subplot(partition_rows,partition_cols, i+1) 
      df.groupby(col).size().plot(kind='pie',autopct="%.1f%%",fontsize=24)
      plt.title(col, fontsize=24)   
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def pie_chart_analysis_big(df,attr_list):
  partition_cols = 1
  partition_rows = 10
  df = df.toPandas()

  fig = plt.figure(figsize=(40,80))

  for i, col in enumerate(attr_list):  
      ax=fig.add_subplot(partition_rows,partition_cols, i+1) 
      df.groupby(col).size().plot(kind='pie', legend=True,autopct="%.1f%%",fontsize=24)
      plt.title(col, fontsize=24)   
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def pie_chart_analysis_wo_legend_big(df,attr_list):
  partition_cols = 1
  partition_rows = 10
  df = df.toPandas()

  fig = plt.figure(figsize=(40,80))

  for i, col in enumerate(attr_list):  
      ax=fig.add_subplot(partition_rows,partition_cols, i+1) 
      df.groupby(col).size().plot(kind='pie',autopct="%.1f%%",fontsize=24)
      plt.title(col, fontsize=24)   
    
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def countplot_analysis(df,x_attr_list,y_col):
  
  partition_cols = 1
  partition_rows = 10
  df = df.toPandas()

  fig=plt.figure(figsize=(30,40))

  for i, col in enumerate(x_attr_list):
    ax = fig.add_subplot(partition_rows,partition_cols, i+1)
    sns.countplot(x=col,hue=y_col,data=df)
    plt.title(col, fontsize=20)
  
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def countplot_analysis_filter_x(df,x_attr_list,y_col,x):
  
  partition_cols = 1
  partition_rows = 10
  
  fig=plt.figure(figsize=(30,40))

  for i, col in enumerate(x_attr_list):
    df1 = df.filter(~(F.col(col)==x))
    df2 = df1.toPandas()
    ax = fig.add_subplot(partition_rows,partition_cols, i+1)
    sns.countplot(x=col,hue=y_col,data=df2)
    plt.title(col, fontsize=20)
  
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def bivariate_histogram_analysis(df,col_list,target_col):
  
  partition_cols = 1
  partition_rows = 10
  
  fig=plt.figure(figsize=(30,40))

  for i, column in enumerate(col_list):
    hist_data = df.select(target_col, column).na.drop().toPandas()
    ax = fig.add_subplot(partition_rows,partition_cols, i+1)
    sns.histplot(data=hist_data, x=column, bins=8, hue=target_col, ax=ax)
    ax.set_title(column)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, title=target_col, loc='upper right')
    ax.set_xlabel(column)
    ax.set_ylabel('Count')
  
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def bivariate_histogram_analysis_2(df,col_list,target_col):
  
  partition_cols = 1
  partition_rows = 10
  
  fig=plt.figure(figsize=(30,40))

  for i, column in enumerate(col_list):
    hist_data = df.select(target_col, column).na.drop().toPandas()
    ax = fig.add_subplot(partition_rows,partition_cols, i+1)
    sns.histplot(data=hist_data, x=column, bins=8, hue=target_col,multiple="stack", ax=ax)
    ax.set_title(column)

    #handles, labels = ax.get_legend_handles_labels()
    #ax.legend(handles, labels, title=target_col, loc='upper right')
    ax.set_xlabel(column)
    ax.set_ylabel('Count')
  
  fig.tight_layout()  
  plt.show()

# COMMAND ----------

def get_categorical_target_correlation(df, attr_list, target_col):
  df = df.toPandas()
  for column in attr_list:
    contingency_table = pd.crosstab(df[column], df[target_col])
    chi2, p_value, _, _ = scipy.stats.chi2_contingency(contingency_table)

    if p_value < 0.05:
      print(f'{column} -> chi-square score: {chi2}, p-value: {p_value} -> No correlation')
    else:
      print(f'{column} -> chi-square score: {chi2}, p-value: {p_value} -> Correlation exists')

# COMMAND ----------

def get_duplicate_attr(attr_list):
  import collections
  print([item for item, count in collections.Counter(attr_list).items() if count > 1])

# COMMAND ----------

def multi_corr_cat_vs_cat(df, label_col):
  list1, list2 = list(), [0]
  for i in range(0,len(label_col)):
    list2.extend([0]*i)
    if i < len(label_col):
      for j in range(i+1,len(label_col)):
        dfx = df.select(col(label_col[i]),col(label_col[j])).toPandas()
        crosstab_result = pd.crosstab(index=dfx[label_col[i]], columns=dfx[label_col[j]])
        association_metric = association(crosstab_result)
        #print("The association variable between",crosstab_result.index.name,"and",crosstab_result.columns.name,"is:",association_metric)
        list2.extend([association_metric])
    list1.append(list2)
    list2 = [0]
  #print(list1)
  dfx = pd.DataFrame(columns=label_col,data=list1,index=label_col)
  return dfx

# COMMAND ----------

def read_parquet_file(path):
  df = spark.read.format("parquet").option("header",'true').load(path)
  display(df.limit(5))
  print("Record Count: ",df.count())
  print("Column Count: ",len(df.columns))

  return df

# COMMAND ----------

def read_csv_file(file_path,delimiter_sign):
  df = spark.read.format("csv").option("header","true").option("delimiter", delimiter_sign).load(file_path)
  display(df.limit(5))
  print("Record Count",df.count())
  print("Record Count: ",len(df.columns))

  return df

# COMMAND ----------

def display_null_values(df):
  #display(df.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) for c in df.columns]).toPandas().transpose())
  print(df.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) for c in df.columns]).toPandas().transpose())

# COMMAND ----------

def get_cat_cols(df, excl_list):
  cat_cols = [item[0] for item in df.dtypes if item[1].startswith('string') and item[0] not in excl_list]
  return cat_cols

# COMMAND ----------

def get_int_cols(df, excl_list):
  int_cols = [item[0] for item in df.dtypes if item[1].startswith('int') and item[0] not in excl_list]
  return int_cols

# COMMAND ----------

def get_cat_num_attr_list(df, exl_list):  
  cat_cols = get_cat_cols(df, exl_list)

  print("Attribute list of Categorical Cols: ", cat_cols)
  print("Number of Attributes of Categorical Cols: ", len(cat_cols))

  int_cols = get_int_cols(df, exl_list)

  print("Attribute list of Numeric Cols: ", int_cols)
  print("Number of Attributes of Numeric Cols: ", len(int_cols))

  return cat_cols, int_cols

# COMMAND ----------

def num_imputation(df,num_cols):
  imputer = Imputer(
    inputCols=num_cols, 
    outputCols=["{}_imputed".format(c) for c in num_cols]
    ).setStrategy("median")

  # Add imputation cols to df
  x_imp_tmp1 = imputer.fit(df).transform(df)
  x_imp_tmp2 = x_imp_tmp1.drop(*num_cols)
  x_int_imp = x_imp_tmp2
  for col_name in num_cols:
    x_int_imp = x_int_imp.withColumnRenamed(col_name+'_imputed',col_name)
  return x_int_imp

# COMMAND ----------

def cat_imputation(df,cat_cols):
  cat_imp_df = df
  for col_name in cat_cols:
      common = cat_imp_df.dropna().groupBy(col_name).agg(F.count("*")).orderBy('count(1)', ascending=False).first()[col_name]
      cat_imp_df = cat_imp_df.withColumn(col_name, F.when(F.isnull(col_name), common).otherwise(cat_imp_df[col_name]))

  return cat_imp_df

# COMMAND ----------

def cat_imputation_2(df,cat_cols):
  cat_imp_df = df
  for col_name in cat_cols:
      common = cat_imp_df.na.drop(subset=[col_name]).groupBy(col_name).agg(F.count("*")).orderBy('count(1)', ascending=False).first()[col_name]
      cat_imp_df = cat_imp_df.withColumn(col_name, F.when(F.isnull(col_name), common).otherwise(cat_imp_df[col_name]))

  return cat_imp_df

# COMMAND ----------

def cat_imputation_3(df,cat_cols):
  cat_imp_df = df
  for col_name in cat_cols:
      cat_imp_df = cat_imp_df.withColumn(col_name, F.when(F.isnull(col_name), 'x').otherwise(cat_imp_df[col_name]))

  return cat_imp_df

# COMMAND ----------

def pre_process_df(df,excl_list):
  cat_cols, int_cols = get_cat_num_attr_list(full_training_df, excl_list)
  
  num_imput_df = num_imputation(df,int_cols)

  display(num_imput_df.limit(5))
  print("Record Count After Numeric Imputation: ",num_imput_df.count())
  print("Column Count After Numeric Imputation: : ",len(num_imput_df.columns))

  cat_imp_df = cat_imputation(num_imput_df,cat_cols)

  display(cat_imp_df.limit(5))
  print("Record Count After Categorical Imputation: : ",cat_imp_df.count())
  print("Column Count After Categorical Imputation: : ",len(cat_imp_df.columns))

  return cat_imp_df, cat_cols, int_cols

# COMMAND ----------

def pre_process_df_2(df,excl_list):
  cat_cols, int_cols = get_cat_num_attr_list(full_training_df, excl_list)
  
  num_imput_df = num_imputation(df,int_cols)

  display(num_imput_df.limit(5))
  print("Record Count After Numeric Imputation: ",num_imput_df.count())
  print("Column Count After Numeric Imputation: : ",len(num_imput_df.columns))

  cat_imp_df = cat_imputation_2(num_imput_df,cat_cols)

  display(cat_imp_df.limit(5))
  print("Record Count After Categorical Imputation: : ",cat_imp_df.count())
  print("Column Count After Categorical Imputation: : ",len(cat_imp_df.columns))

  return cat_imp_df, cat_cols, int_cols

# COMMAND ----------

def pre_process_df_3(df,excl_list):
  cat_cols, int_cols = get_cat_num_attr_list(df, excl_list)
  
  num_imput_df = num_imputation(df,int_cols)

  display(num_imput_df.limit(5))
  print("Record Count After Numeric Imputation: ",num_imput_df.count())
  print("Column Count After Numeric Imputation: : ",len(num_imput_df.columns))

  cat_imp_df = cat_imputation_3(num_imput_df,cat_cols)

  display(cat_imp_df.limit(5))
  print("Record Count After Categorical Imputation: : ",cat_imp_df.count())
  print("Column Count After Categorical Imputation: : ",len(cat_imp_df.columns))

  return cat_imp_df, cat_cols, int_cols

# COMMAND ----------

def pre_process_cat_only_df(df,excl_list):
  cat_cols = get_cat_cols(df, excl_list)

  print("Attribute list of Categorical Cols: ", cat_cols)
  print("Number of Attributes of Categorical Cols: ", len(cat_cols))

  cat_imp_df = cat_imputation(df,cat_cols)

  display(cat_imp_df.limit(5))
  print("Record Count After Categorical Imputation: : ",cat_imp_df.count())
  print("Column Count After Categorical Imputation: : ",len(cat_imp_df.columns))

  return cat_imp_df, cat_cols

# COMMAND ----------

def pre_process_int_only_df(df,excl_list):
  int_cols = get_int_cols(df, excl_list)

  print("Attribute list of Categorical Cols: ", int_cols)
  print("Number of Attributes of Categorical Cols: ", len(int_cols))

  num_imput_df = num_imputation(df,int_cols)

  display(num_imput_df.limit(5))
  print("Record Count After Numeric Imputation: ",num_imput_df.count())
  print("Column Count After Numeric Imputation: : ",len(num_imput_df.columns))

  return num_imput_df, int_cols

# COMMAND ----------

def create_vector(df,cat_cols, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  assembler_inputs = si_cols +["num_cols"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,num_assembler,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_cat_only(df,cat_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  assembler_inputs = si_cols
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_oh(df,cat_cols, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  encoder = OneHotEncoder(inputCols=si_cols, outputCols=[i+"_classVec" for i in cat_cols],handleInvalid='keep')
  oh_cols=[i+"_classVec" for i in cat_cols]

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  assembler_inputs = oh_cols +["num_cols"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,encoder,num_assembler,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_pca_num(df,cat_cols, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  pca_num = PCA(inputCol = "num_cols",outputCol = "num_pca",k=5)

  assembler_inputs = si_cols +["num_pca"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,num_assembler,pca_num,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_pca_num_cat(df,cat_cols, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  encoder = OneHotEncoder(inputCols=si_cols, outputCols=[i+"_classVec" for i in cat_cols],handleInvalid='keep')
  oh_cols=[i+"_classVec" for i in cat_cols]

  cat_assembler = VectorAssembler(inputCols = oh_cols,outputCol = "cat_cols_assm")

  pca_cat = PCA(inputCol = "cat_cols_assm",outputCol = "cat_pca",k=10)

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  pca_num = PCA(inputCol = "num_cols",outputCol = "num_pca",k=5)

  assembler_inputs = ['cat_pca'] +["num_pca"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,encoder,cat_assembler,pca_cat,num_assembler,pca_num,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_pca_num_cat2(df,cat_cols, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  indexer = StringIndexer(inputCols=cat_cols, outputCols=[i+"_index" for i in cat_cols],handleInvalid='keep')
  si_cols=[i+"_index" for i in cat_cols]

  cat_assembler = VectorAssembler(inputCols = si_cols,outputCol = "cat_cols_assm")

  pca_cat = PCA(inputCol = "cat_cols_assm",outputCol = "cat_pca",k=10)

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  pca_num = PCA(inputCol = "num_cols",outputCol = "num_pca",k=5)

  assembler_inputs = ['cat_pca'] +["num_pca"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,indexer,cat_assembler,pca_cat,num_assembler,pca_num,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def create_vector_int_only(df, int_cols,output_col):
  test_train_df = df

  op_indexer = StringIndexer(inputCols=output_col, outputCols=[i+"_op_index" for i in output_col],handleInvalid='keep')
  op_si_cols=[i+"_op_index" for i in output_col]

  num_assembler = VectorAssembler(inputCols = int_cols,outputCol = "num_cols")

  assembler_inputs = ["num_cols"]
  assembler = VectorAssembler(inputCols=assembler_inputs, outputCol="features")

  stages = [op_indexer,num_assembler,assembler]

  pipeline = Pipeline(stages = stages)
  pipelineModel = pipeline.fit(test_train_df)
  test_train_df_encoded = pipelineModel.transform(test_train_df)

  print("Record Count After Encoding: ",test_train_df_encoded.count())
  display(test_train_df_encoded.limit(5))

  group_by_list = output_col + op_si_cols
  display(test_train_df_encoded.groupBy(group_by_list).count())

  return test_train_df_encoded

# COMMAND ----------

def train_model(df,target_variable):
  train_df, test_df = df.randomSplit([0.7,0.3], seed = 2018)
  print("Training Dataset Count: ", train_df.count())
  print("Testing Dataset Count: ", test_df.count())

  display(train_df.groupBy(col(target_variable)).count())
  display(test_df.groupBy(col(target_variable)).count())

  rf_classifier = RandomForestClassifier(featuresCol='features',labelCol=target_variable,maxBins=27270)
  rf_Model = rf_classifier.fit(train_df)

  predictions = rf_Model.transform(test_df)
  predictions.select(target_variable,'rawPrediction','probability','prediction').toPandas().head(5)

  print("Confusion Matrix: ")
  display(predictions.groupBy(col(target_variable),col('prediction')).count())

  df_accuracy = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="accuracy").evaluate(predictions)
  print('Accuracy: ',df_accuracy)

  df_precision = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="weightedPrecision").evaluate(predictions)
  print('Precision: ',df_precision)

  df_recall = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="truePositiveRateByLabel").evaluate(predictions)
  print('Recall: ',df_recall)

  return rf_Model

# COMMAND ----------

def train_model_lgbm(df,target_variable):
  train_df, test_df = df.randomSplit([0.7,0.3], seed = 2018)
  print("Training Dataset Count: ", train_df.count())
  print("Testing Dataset Count: ", test_df.count())

  display(train_df.groupBy(col(target_variable)).count())
  display(test_df.groupBy(col(target_variable)).count())

  lgbm_classifier = LightGBMClassifier(featuresCol='features',labelCol=target_variable)
  lgbm_Model = lgbm_classifier.fit(train_df)

  predictions = lgbm_Model.transform(test_df)
  predictions.select(target_variable,'rawPrediction','probability','prediction').toPandas().head(5)

  print("Confusion Matrix: ")
  display(predictions.groupBy(col(target_variable),col('prediction')).count())

  df_accuracy = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="accuracy").evaluate(predictions)
  print('Accuracy: ',df_accuracy)

  df_precision = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="weightedPrecision").evaluate(predictions)
  print('Precision: ',df_precision)

  df_recall = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="truePositiveRateByLabel").evaluate(predictions)
  print('Recall: ',df_recall)

  df_f1 = MulticlassClassificationEvaluator(labelCol=target_variable,
                                               metricName="f1").evaluate(predictions)
  print('F1 Score: ',df_f1)

  return lgbm_Model

# COMMAND ----------

def feature_importance_ps(encoded_df,model):
  feat_imp = model.featureImportances.toArray()
  #display(feat_imp)
  feat_imp_df = spark.createDataFrame(feat_imp,schema=['feature_importance'])
  feat_imp_df = feat_imp_df.withColumn("idx",row_number().over(Window.orderBy(monotonically_increasing_id()))-1).sort(desc('feature_importance'))
  #display(feat_imp_df)

  df_nom_ind, df_num_ind = False, False
  col_x = ['idx','name']
  schm = encoded_df.schema["features"].metadata["ml_attr"]["attrs"]
  #display(schm)
  for k,v in schm.items():
    if k == "nominal":
      df_nominal = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_nom_ind = True
      #display(df_nominal.limit(5))
    elif k == "numeric":
      df_numeric = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_num_ind = True
      #display(df_numeric.limit(5))
  
  if df_num_ind and df_nom_ind:
    print('check 3')
    df_all = df_nominal.union(df_numeric)
  elif df_nominal and ~df_num_ind:
    print('check 1')
    df_all = df_nominal
  elif df_num_ind and ~df_nom_ind:
    print('check 2')
    df_all = df_numeric

  feature_imp_df = feat_imp_df.join(df_all,on='idx',how= "inner").sort(desc('feature_importance'))
  return feature_imp_df

# COMMAND ----------

def feature_importance_2(encoded_df,model):
  feat_imp = model.featureImportances.toArray()
  #display(feat_imp)
  feat_imp_df = spark.createDataFrame(feat_imp,schema=['feature_importance'])
  feat_imp_df = feat_imp_df.withColumn("idx",row_number().over(Window.orderBy(monotonically_increasing_id()))-1).sort(desc('feature_importance'))
  #display(feat_imp_df)

  df_nom_ind, df_num_ind, df_bin_ind = False, False, False
  col_x = ['idx','name']
  schm = encoded_df.schema["features"].metadata["ml_attr"]["attrs"]
  #display(schm)
  for k,v in schm.items():
    #print("k: ",k)
    #print("v: ",v)
    if k == "nominal":
      df_nominal = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_nom_ind = True
      #display(df_nominal.limit(5))
    elif k == "numeric":
      df_numeric = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_num_ind = True
      #display(df_numeric.limit(5))
    elif k == "binary":
      #print("inside binary")
      df_binary = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_bin_ind = True
      #display(df_binary.limit(5))
  
  if df_bin_ind:
    if df_nom_ind and ~df_num_ind:
      print('check 4')
      df_all = df_nominal.union(df_binary)
    elif df_num_ind and ~df_nom_ind:
      print('check 5')
      df_all = df_numeric.union(df_binary)
    elif ~df_nom_ind and ~df_num_ind:
      print('check 6')
      df_all = df_binary
    elif df_num_ind and df_nom_ind:
      print('check 7')
      df_all = df_nominal.union(df_numeric).union(df_binary)
  else:
    if df_num_ind and df_nom_ind:
      print('check 3')
      df_all = df_nominal.union(df_numeric)
    elif df_nom_ind and ~df_num_ind:
      print('check 1')
      df_all = df_nominal
    elif df_num_ind and ~df_nom_ind:
      print('check 2')
      df_all = df_numeric
  
  
  feature_imp_df = feat_imp_df.join(df_all,on='idx',how= "inner").sort(desc('feature_importance'))
  return feature_imp_df

# COMMAND ----------

def feature_importance_int_only(encoded_df,model):
  feat_imp = model.featureImportances.toArray()
  #display(feat_imp)
  feat_imp_df = spark.createDataFrame(feat_imp,schema=['feature_importance'])
  feat_imp_df = feat_imp_df.withColumn("idx",row_number().over(Window.orderBy(monotonically_increasing_id()))-1).sort(desc('feature_importance'))
  #display(feat_imp_df)

  df_nom_ind, df_num_ind = False, False
  col_x = ['idx','name']
  schm = encoded_df.schema["features"].metadata["ml_attr"]["attrs"]
  #display(schm)
  for k,v in schm.items():
    if k == "numeric":
      df_numeric = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_num_ind = True
      #display(df_numeric.limit(5))
  
  if df_num_ind:
    #print('check 3')
    df_all = df_numeric

  feature_imp_df = feat_imp_df.join(df_all,on='idx',how= "inner").sort(desc('feature_importance'))
  return feature_imp_df

# COMMAND ----------

def feature_importance_lgbm(encoded_df,model):
  feat_imp = np.array(model.getFeatureImportances())
  #display(feat_imp)
  feat_imp_df = spark.createDataFrame(feat_imp,schema=['feature_importance'])
  feat_imp_df = feat_imp_df.withColumn("idx",row_number().over(Window.orderBy(monotonically_increasing_id()))-1).sort(desc('feature_importance'))
  #display(feat_imp_df)

  df_nom_ind, df_num_ind = False, False
  col_x = ['idx','name']
  schm = encoded_df.schema["features"].metadata["ml_attr"]["attrs"]
  #display(schm)
  for k,v in schm.items():
    if k == "nominal":
      df_nominal = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_nom_ind = True
      #display(df_nominal.limit(5))
    elif k == "numeric":
      df_numeric = spark.createDataFrame(data=schm[k]).select(*col_x)
      df_num_ind = True
      #display(df_numeric.limit(5))
  
  if df_num_ind and df_nom_ind:
    print('check 3')
    df_all = df_nominal.union(df_numeric)
  elif df_nominal and ~df_num_ind:
    print('check 1')
    df_all = df_nominal
  elif df_num_ind and ~df_nom_ind:
    print('check 2')
    df_all = df_numeric

  feature_imp_df = feat_imp_df.join(df_all,on='idx',how= "inner").sort(desc('feature_importance'))
  return feature_imp_df

# COMMAND ----------

def plot_feature_imp(df):
#plot feature importance
  feat_imp_df = df.select(col('name'),col('feature_importance')).toPandas().sort_values(by=['feature_importance'],ascending=False)
  display(feat_imp_df)

  plt.figure(figsize=(20,10))
  ax = sns.barplot(data=feat_imp_df,y='name',x='feature_importance')
  for i in ax.containers:
    ax.bar_label(i,)

# COMMAND ----------

def create_load_delta_table(df,table_name,table_schema,drop_flg='N'):
  ml_poc_folder_path = "dbfs:/user/sonam.wadhwani@data-axle.com/ml_poc"

  database_name = "ml_poc_sonamw"
  database_location = ml_poc_folder_path + '/ml_poc_location.db'

  spark.sql(f"USE {database_name};")

  if drop_flg == 'Y':
    spark.sql(f"DROP table {table_name};")

  spark.sql(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_schema}) USING DELTA;")

  df.createOrReplaceTempView('full_data_temp_view')
  spark.sql(f"USE {database_name};")

  spark.sql(f"""MERGE INTO {table_name} a
      USING full_data_temp_view b
      ON a.CE_Selected_Individual_ID=b.CE_Selected_Individual_ID
      WHEN MATCHED
      THEN UPDATE SET *
      WHEN NOT MATCHED
      THEN INSERT *""")

# COMMAND ----------

def create_load_delta_table_hh(df,table_name,table_schema,drop_flg='N'):
  ml_poc_folder_path = "dbfs:/user/sonam.wadhwani@data-axle.com/ml_poc"

  database_name = "ml_poc_sonamw"
  database_location = ml_poc_folder_path + '/ml_poc_location.db'

  spark.sql(f"USE {database_name};")

  if drop_flg == 'Y':
    spark.sql(f"DROP table {table_name};")

  spark.sql(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_schema}) USING DELTA;")

  df.createOrReplaceTempView('full_data_temp_view')
  spark.sql(f"USE {database_name};")

  spark.sql(f"""MERGE INTO {table_name} a
      USING full_data_temp_view b
      ON a.CE_Household_ID=b.CE_Household_ID
      WHEN MATCHED
      THEN UPDATE SET *
      WHEN NOT MATCHED
      THEN INSERT *""")

# COMMAND ----------

def normalize_log10(df,excl_list):
  int_cols = get_int_cols(df, excl_list)

  for col_name in cat_cols:
      df = df.withColumn(col_name, F.log10(F.col(col_name)))

  return df

# COMMAND ----------

def normalize_loge(df,excl_list):
  int_cols = get_int_cols(df, excl_list)

  for col_name in cat_cols:
      df = df.withColumn(col_name, F.log(F.col(col_name)))

  return df

# COMMAND ----------

def power_transformation(df,excl_list,key_col):
  cat_cols, int_cols = get_cat_num_attr_list(df, excl_list)
  
  pd_df=df.toPandas()
  pow_trans_cols=[]

  pt = PowerTransformer()
  num_pow_arr = pt.fit_transform(pd_df[int_cols])

  #pow_trans_cols=[i+"_pow" for i in int_cols]

  num_pow_pd_df = pd.DataFrame(num_pow_arr,columns=int_cols)
  num_pow_pd_df[key_col]=list(pd_df[key_col])
  num_pow_df=spark.createDataFrame(num_pow_pd_df)

  cat_df=df.select(*cat_cols,*excl_list)
  
  pt_df = cat_df.join(num_pow_df,on=key_col,how='inner')

  #for col_name in int_cols:
  #  pt_df2 = pt_df.withColumnRenamed(col_name+'_pow',col_name)

  return pt_df

# COMMAND ----------

def extract_prob(v):
    try:
        return float(v[1])  # Your VectorUDT is of length 2
    except ValueError:
        return None
      
extract_prob_udf = udf(extract_prob, DoubleType())

# COMMAND ----------

def get_metrics(pred_df,actual_col,predicted_col):
  pred_df.crosstab(actual_col,predicted_col).display()
  pred_df = pred_df.withColumn(predicted_col,F.col(predicted_col).cast('int'))
  pred_df = pred_df.withColumn(actual_col,F.col(actual_col).cast('int'))

  pandas_df = pred_df.select(actual_col, predicted_col).toPandas()
  
  # Calculate confusion matrix using sklearn
  cm = confusion_matrix(pandas_df[actual_col], pandas_df[predicted_col])
  print(cm)
  normalized_cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

  # Create a pandas DataFrame from the confusion matrix
  cm_df = pd.DataFrame(normalized_cm, index=['0', '1'], columns=['0', '1'])

  # Plot the confusion matrix using Seaborn
  plt.figure(figsize=(8, 6))
  sns.heatmap(cm_df, annot=True, cmap='Blues')
  plt.title('Normalized Confusion Matrix')
  plt.xlabel('Predicted')
  plt.ylabel('Actual')
  plt.show()

  report = classification_report(pandas_df[actual_col], pandas_df[predicted_col])

  # Print the classification report
  print(report)

# COMMAND ----------

def point_biserial_correlation(df,num_attr,target_col):
  list2 = list()
  col_list = ['Column_Name','Correlation_Value']
  for c in num_attr:
    list1 = list() 
    df_dropna = df.dropna(subset=[c])
    df_count = df_dropna.count()
    list1.append(c)
    if df_count > 1:

      df1 = df_dropna.select(target_col)
      df1_pd = df1.toPandas()
      df1_np = df1_pd[target_col].tolist()

      df2 = df_dropna.select(c)
      df2_pd = df2.toPandas()
      df2_np = df2_pd[c].tolist()

      x,_ = stats.pointbiserialr(df1_np, df2_np)
      list1.append(str(np.round(x,3)))
      list2.append(list1)
    else:
      list1.append("0")
      list2.append(list1)

  dfx = spark.createDataFrame(list2,schema=col_list)
  return dfx

# COMMAND ----------

def combine_census_attr(df, col_list):

  for c in col_list:
    col1 = c + "_1"
    col2 = c + "_2"
    col3 = c + "_3"
    col4 = c + "_4"

    df = df.withColumn(c+"_eng",when(col(col4).isNotNull(),col(col4)).when(col(col3).isNotNull(),col(col3)).when(col(col2).isNotNull(),col(col2)).when(col(col1).isNotNull(),col(col1)).otherwise(lit(-1)))
    
  df = df.replace({'-1': None}, subset=[c+"_eng" for c in col_list])

  return df