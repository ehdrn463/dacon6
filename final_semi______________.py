import os
import pandas as pd
import numpy as np
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import math
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
import tensorflow as tf 
import math

def mkMonthData():

    daybyday = pd.read_csv("Regular_Season_Batter_Day_by_Day.csv")
    daybyday['1B'] = daybyday['H'] - daybyday['2B'] - daybyday['3B'] - daybyday['HR']
    for i in ['opposing_team','SB','CS']:
        del daybyday[i]
    sub = pd.read_csv("/data/submission.csv")
    # sub 파일에 없는 선수 걸러내기
    dayNamelist=list(daybyday["batter_name"].unique())
    subNameslist= list(set(sub['batter_name']))

    namelist=[]
    for i in dayNamelist:
        if i in subNameslist:
            namelist+=[i]

    delrow=[]
    for i in range(len(daybyday)):
        if daybyday["batter_name"][i] in namelist:
            continue
        else:
            delrow+=[i]
    daybyday = daybyday.drop(delrow,0)
    month = pd.DataFrame(columns=('batter_id', 'batter_name','year', 'month', 'am_avg','avg', 'AB', 'R', 'H', '1B', '2B', '3B','HR', 'RBI', 'BB', 'HBP', 'SO', 'GDP'))
    idx=0
    for n in namelist:
        a=daybyday.loc[daybyday["batter_name"]==n,]
        year=sorted(list(a['year'].unique()))
        for y in year:
            b=a.loc[a["year"]==y,]
            for i in range(3,11):
                c=b.loc[b["date"]//1==i,]
                if len(c):
                    state=list(c[['avg2', 'AB', 'R', 'H', '1B', '2B', '3B','HR', 'RBI', 'BB', 'HBP', 'SO', 'GDP']].sum(axis=0))
                    state[0]=c["avg2"].iloc[-1]
                    if state[1]:
                        avg1=round(state[3]/state[1],3)
                    else:
                        avg1=0
                    state=[c["batter_id"].iloc[0],n,y,i]+[avg1]+state
                    month.loc[idx]=state
                    idx+=1
    BABIP=[]
    SLG=[]
    OBP=[]
    for i in range(len(month)):
        if (month['H'][i] - month['HR'][i]) and (month['AB'][i] - month['SO'][i] -month['HR'][i]):
            BABIP+= [round((month['H'][i] - month['HR'][i]) / (month['AB'][i] - month['SO'][i] -month['HR'][i]),3)]
        else:
            BABIP+=[0]
            
        if (month['1B'][i] + month['2B'][i] + month['3B'][i] + month['HR'][i]) and (month['AB'][i]):
            SLG+= [round((month['1B'][i] + 2*month['2B'][i] + 3*month['3B'][i] + 4*month['HR'][i]) / (month['AB'][i]),3)]
        else:
            SLG+=[0]   
            
        if (month['H'][i] + month['BB'][i] + month['HBP'][i]) and (month['AB'][i] + month['BB'][i] + month['HBP'][i]):
            OBP+= [round((month['H'][i] + month['BB'][i] + month['HBP'][i]) / (month['AB'][i] + month['BB'][i] + month['HBP'][i]),3)]
        else:
            OBP+=[0] 
            
    month['BABIP']=BABIP
    month['SLG']=SLG
    month['OBP']=OBP

    mean=[]
    for c in range(3):
        mean.append([])
        
    for i in range(len(namelist)):
        a=month.loc[month["batter_name"]==namelist[i],][["BABIP",'SLG','OBP']].values
        for j in range(len(a)):
            for c in range(3):
                if j==0:
                    mean[c]+=[a[0][c]]
                else:
                    mean[c]+=[round((a[j][c]+(mean[c][j-1]*j))/(j+1),3)]
                    
    for idx,col in enumerate(["BABIP",'SLG','OBP']):
        month["am_"+col]=mean[idx]

    return month

# ======== corre_OPS Functions
def get_BABIP(alist):
    BABIP = 0
    if (alist['H'] - alist['HR']) and (alist['AB'] - alist['SO'] - alist['HR']):
        BABIP+= round((alist['H'] - alist['HR']) / (alist['AB'] - alist['SO'] -alist['HR']),3)
    return BABIP

def get_OPS_model(reg_batterFile):

    seed = 0
    np.random.seed(seed)
    tf.set_random_seed(seed)

    id_arr = reg_batterFile['batter_id'].unique()
    id_arr = id_arr.tolist()

    main_col = [
            'avg','AB','R','H',
            '2B','3B','HR','RBI','BB',
            'HBP','SO','GDP','SLG',
            'OBP'
            ]

    alist = []

    for bat_id in id_arr:
        nptf = reg_batterFile.loc[reg_batterFile['batter_id'] == bat_id]
        nptf = nptf.fillna(0)
        recentData = nptf.iloc[-1]
        recentData['BABIP'] = get_BABIP(recentData)
        extract_data = []
        extract_data.append(recentData['BABIP'])
        for col in main_col:
            if recentData[col] == '-':
                recentData[col] = 0
            extract_data.append(recentData[col])
        
        alist.append(extract_data)

    df = pd.DataFrame(alist)
    dataset = df.values

    X = dataset[:,:14]
    Y = dataset[:,14]

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=seed)

    modelOPS = Sequential()
    modelOPS.add( Dense(30, input_dim=14, activation='relu') )
    modelOPS.add( Dense(6, activation='relu') )
    modelOPS.add( Dense(1) )

    modelOPS.compile(loss='mean_squared_error',
                    optimizer='adam')


    modelOPS.fit(X_train, Y_train, epochs=200, batch_size=10)


    return modelOPS


# ========= Predict each col Functions
def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i + look_back)]
        dataX.append(a)
        dataY.append(dataset[i + look_back])
    return np.array(dataX), np.array(dataY)

def predcit_next_DBD(nptf, column, look_back=1):
    
    # normalization
    scaler = MinMaxScaler(feature_range=(0, 1))
    nptf = nptf[column].values
    nptf = nptf.reshape(-1,1)
    nptf = scaler.fit_transform(nptf)

    train_size = int(len(nptf) * 0.9)
    test_size = len(nptf) - train_size
    train, test = nptf[0:train_size], nptf[train_size:len(nptf)]

    # create dataset for learning
    trainX, trainY = create_dataset(train, look_back)
    testX, testY = create_dataset(test, look_back)
    trainX = np.reshape(trainX, (trainX.shape[0], 1, trainX.shape[1]))
    testX = np.reshape(testX, (testX.shape[0], 1, testX.shape[1]))
    
    # simple lstm network learning
    model = Sequential()
    model.add(LSTM(8, input_shape=(1, look_back)))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    model.fit(trainX, trainY, epochs=5, batch_size=1, verbose=2)

    
    # 향후 10달의 평균 예측
    look_ahead = 10
    res = nptf.copy()
    res = create_dataset(res,1)
    res = res[0]

    res = np.reshape(res, (res.shape[0], 1, res.shape[1]))
    pre = model.predict(res)
    res = np.append(res, [[pre[-1]]])
    res = np.reshape(res, (res.shape[0], 1))

    for _ in range(look_ahead):
        res = np.reshape(res, (res.shape[0], 1, res.shape[1]))
        pre = model.predict(res)
        res = np.append(res, [[pre[-1]]])
        res = np.reshape(res, (res.shape[0], 1))
    pre = scaler.inverse_transform(pre)

    return pre[-1]

# ========== MAAIN

# Main file loader
sub_fileDR = './data/submission.csv'
reg_batter_fileDR = './data/Regular_Season_Batter.csv'

submissionFile = pd.read_csv(sub_fileDR)
reg_batterFile = pd.read_csv(reg_batter_fileDR)

bat_id = submissionFile['batter_id'].unique()
bat_id = bat_id.tolist()

Month_data = mkMonthData()
mon_data_bat_id = Month_data['batter_id'].unique()

modelOPS = get_OPS_model(reg_batterFile)

main_col = [
        'avg','AB','R','H',
        '2B','3B','HR','RBI','BB',
        'HBP','SO','GDP','SLG'
        ]

for eachId in bat_id:
    if eachId in mon_data_bat_id:
        

        # day_by_day 데이터 예측 또는 평균 값 도출 후 OPS 예측
        look_back = 1
        eachPlayer_record = [eachId]
        nptf = Month_data.loc[Month_data['batter_id'] == bat_id]
        for col in main_col: 
            if len(nptf) > 20:
                res = predcit_next_DBD(nptf, col, look_back)
                eachPlayer_record.append(res)
            else:
                res = nptf[col].mean()
                eachPlayer_record.append(res)
        
        # ToDo LIST
        # eachPlayer_record -> reshape 과정 거쳐야 함
        final_PL_OPS = modelOPS.predict(eachPlayer_record)
        print('eachId: ', eachId, "OPS: ", final_PL_OPS)



    
    else:
		# Not sure
        nptf = reg_batterFile.loc[reg_batterFile['batter_id'] == eachId]
        final_PL_OPS = nptf.iloc[-1]
        print(final_PL_OPS)
