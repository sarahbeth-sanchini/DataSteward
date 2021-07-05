#!/usr/bin/env python
# coding: utf-8

# ## Bayer Case Study - Snaffleflax
# ##### Sarah Beth Sanchini - July 2021
# **Goal**: Combine JSON and CSV data into a single file
# 
# **Specifications**: Include columns for: 
# 
# > 1. Market Share
# 2. Lagged X-Month Average of Market Share
# 3. Lagged X-Month Sum of Weighted Events

# ###### Start with importing all libraries 

# In[47]:


import pandas as pd
import json
import csv
import numpy as np
import os
import glob
import datetime
pd.options.mode.chained_assignment = None


# ###### Portion of code for user to set variables

# In[48]:


#directory filepaths
in_filepath = "/Users/sarahbeth/Desktop/Bayer/data"
out_filepath = "/Users/sarahbeth/Desktop/Bayer/"

#column specifications: Lagged X-Month Average of Market Share 
### How many months would you like to lag? ###  
x1 = 3 

#column specifications: Lagged X-Month Sum of Weighted Events
### How many months would you like to lag? ###  
x2 = 1


# <div style="page-break-after: always;"></div>

# ###### Read in multiple JSON files by parsing the directory
# > Each JSON files is opened and saved to a list, which is then combined into one dataframe object

# In[49]:


#create list of all files ending with .json
file_list = glob.glob(in_filepath + "/*.json")
#read in CRM data
df_crm = pd.read_csv(in_filepath +'/crm_data.csv')


# In[50]:


#open JSON files
dfs = [] # an empty list to store the data frames
for file in file_list:
    json_file1 = open(file)
    json_data1 = json.load(json_file1)
    df1 = pd.read_json(json_data1[0]) # json was in a -1 list (double-encoded) so specify index
    dfs.append(df1) # append the data frame to the list

df = pd.concat(dfs, ignore_index=True) # concatenate all the data frames in the list
df.head()


# ###### Data Cleaning
# > Product Name column should only have 4 unique names

# In[51]:


#data exploration - product name
df.product_name.unique()


# In[52]:


#clean product_name
df = df.replace({"Globbrin":"Globberin", " Globberin":"Globberin","vorbulon.":"Vorbulon","Beebliz%C3%B6x":"Beeblizox","Snafulopromazide-b (Snaffleflax)":"Snaffleflax"})


# ###### Create column for Market Share 
# > 1. Calculate total units sold over 18 month period
# 2. Calculate each row entry's market share (row's units sold / total units sold)

# In[53]:


#calculate each row's market share
total_MS = df['unit_sales'].sum()
df['marketshare'] = df['unit_sales']/total_MS
df.head()


# ###### Create column for Lagged X-Month Average of Market Share
# > 1. Calculate the number of days for the lagged period as Python does not support rolling month calculations
# 2. For each row, calculate the rolling average of the specified time frame

# In[54]:


#sort data
df = df.sort_values(by="created_at")
df.head()


# In[55]:


## need to convert months to days
in_x1 = str(x1*30)
in_x1 = in_x1 + "D"

#calculate rolling sum and count of occurences in the month
df2 = df.set_index('created_at').rolling(in_x1)['marketshare'].agg({'sum','count'})
#calculati
df2['lagged x-month avg marketshare'] = df2['sum']/df2['count']
df2.head()


# In[56]:


#merge dataframes together
df_merged = pd.merge(df,df2, on=['created_at'])
df_merged.head()


# ### CRM Data Pre-Processing

# ###### Create column for Lagged X-Month Weighted Sum of Events
# > **Specifications**: Column will be a comma separated list of 3 values with the following format:   
# (F2F, Group Call, Workplace Events) 
# 
# > **Calculation**: 
# >1. Calculate the total number of events
# 2. Calculate the total number of events per event type
# 3. Calculate weights for each event type (number of particular event type / sum of all events)
# 4. Calculate weighted value of each type of event *per day* (daily sum of particular event * event weight 

# In[57]:


#covert date to datetime format 
df_crm['date']= pd.to_datetime(df_crm['date'])
#sort data
df_crm = df_crm.sort_values(by="date")
df_crm = df_crm.reset_index(drop=True)
df_crm.head()


# ###### Calculate values for each date
# >There are 508 unique dates in the file
# 1. Aggregate different event types per day
# 2. Calculate total number of events per day
# 3. Calculate the weights of each type of event based on given timeframe (lag)

# In[58]:


#groupby event type
df_gp = df_crm.groupby(['date'])['event_type'].value_counts().unstack().fillna(0).astype(int)
df_gp.reset_index(inplace = True)


# In[59]:


#create total_events column
for i in df_gp.index:
    df_gp['total_events'] = df_gp['f2f'] + df_gp ['group call'] + df_gp['workplace event']
df_gp.head()


# In[60]:


#set event_date as index to perform rolling operations
df_gp.rename(columns={'date': 'event_date'}, inplace=True)
df_gp = df_gp.set_index('event_date')


# In[61]:


#set input lag: need to convert months to days
in_x2 = str((x2+1)*30)
in_x2 = in_x2 + "D"


# In[62]:


#calculate weighted sum of each type of event:
#Example: #f2f events * (#f2fevents / #total events)

column_names = ["f2f_weighted", "group_weighted", "workplace_weighted"]
df_gpd = pd.DataFrame(columns = column_names)

df_gpd['f2f_weighted'] = (df_gp['f2f'].rolling(window=in_x2).sum())* ((df_gp['f2f'].rolling(window=in_x2).sum())/(df_gp['total_events'].rolling(window=in_x2).sum())) 
df_gpd['group_weighted'] = (df_gp['group call'].rolling(window=in_x2).sum())* ((df_gp['group call'].rolling(window=in_x2).sum())/(df_gp['total_events'].rolling(window=in_x2).sum())) 
df_gpd['workplace_weighted'] = (df_gp['workplace event'].rolling(window=in_x2).sum())* ((df_gp['workplace event'].rolling(window=in_x2).sum())/(df_gp['total_events'].rolling(window=in_x2).sum()))

#join the 3 weighted values to create comma separated output column
df_gpd['weighted_values (f2f,grp call, wkplace)'] = df_gpd.apply(lambda x: ','.join(x.dropna().astype(str).values), axis=1)


# In[63]:


#reset index and make date column
df_gpd = df_gpd.reset_index()
df_gpd.head()


# ###### Create output file
# > Merge dataframes together and output as CSV file.  
# Inner join on date

# In[64]:


#set up columns to merge
df_merged.rename(columns={'created_at':'date1'}, inplace=True)
df_gpd.rename(columns={'event_date':'date1'}, inplace=True)
df_output = pd.concat([df_merged,df_gpd])

df_output = df_output.sort_values(by='date1')
df_output.reset_index(inplace=True)


# In[68]:


#cleanup columns to export
df_output.rename(columns={'date1':'created_at'}, inplace=True)
df_output.drop(columns=['index', 'count','sum','f2f_weighted','group_weighted','workplace_weighted'], axis = 1,inplace=True)
df_output.head()


# In[71]:


#write to csv
df_output.to_csv (out_filepath +'/final_output.csv')

