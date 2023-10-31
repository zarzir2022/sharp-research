import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from PIL import Image
import time

pd.set_option('display.max_rows', None)

df = pd.read_excel("ParsedData.xlsx")
# Прежде всего проверим компанию на выбросы
# Для этого воспользуемся методом describe, чтобы сделать
# Срез статистики. Нас интересуют выбросы именно в столбце NPV
#Чтобы проверить, есть ли выбросы, найдём 1 и 3-ий квартиль и сравним их с
# максимальным и минимальным значением соответственно

def outliersCheck(df, column):
    df = df
    column = column
    if df[column].quantile(0.25) > min(df[column]) and df[column].quantile(0.75) < max(df[column]):
        print("Обнаружены выбросы. Начинаем нормализацию...\n")
        time.sleep(3)
        return True
    else:
        print("Выбросы не обнаружены")
        return False

def outliersCleaner(df, column):
    df = df
    column = column
    Q1 = df[column].quantile(q=.25)
    Q3 = df[column].quantile(q=.75)
    IQR = Q3-Q1
    LimMax = Q3+1.5*IQR
    LimMin = Q1-1.5*IQR
    dfClean = df[(df[column]<LimMax) & (df[column]>LimMin)].reset_index(drop=True)
    outliers = df[(df[column]>LimMax) | (df[column]<LimMin)].reset_index(drop=True)
    return dfClean, outliers

def main():
    column = "NPV"
    outliersCheck(df, column)
    dfClean, outliers = outliersCleaner(df, column)
    print(dfClean)
    print("\nДанные очищены!\n Выбросами оказались следующие значения:")
    print(outliers)

if __name__ == "__main__":
     main()
