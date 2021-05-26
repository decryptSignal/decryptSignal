#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
import json
import math
import ntpath
import os
import pathlib
import re
import sqlite3
import sys
from distutils.dir_util import copy_tree
from glob import glob
from pathlib import Path
import pandas as pd

##  This code is also available, as source code or compiled binary, at https://github.com/decryptSignal/decryptSignal

html = ""
exe_path = os.path.dirname(os.path.realpath(__file__))


def iOS(db, attachmentPath):
    global html

    print("Creating report")
    db_path = os.path.dirname(os.path.realpath(db))
    conn = sqlite3.connect(db)
    messagesQuery = """select 
        CASE 
            when authorPhoneNumber is NULL then "Local User" 
            else authorPhoneNumber 
            end "Phone Number",
        datetime(model_TSInteraction.receivedAtTimestamp/1000, 'unixepoch') as "Received At Timestamp", 
        datetime(model_TSInteraction.timestamp/1000, 'unixepoch') as Timestamp,
        CASE
            when body is NULL then ""
            else body
            end Body,
        CASE
            when messageType is "3" then "Group Created"
            when messageType is "7" then "Oklart"
            when messageType is NULL then ""
            else messageType
            end "Message Type",
        CASE 
            when callType is "1" then "Incoming Call"
            when callType is "2" then "Outgoing Call"
            when callType is "3" then "Missed Incoming Call"
            when callType is "7" then "Rejected Incoming Call"
            when callType is "8" then "Outgoing Call (No answer)"
            else ""
            end "Call Type",
        model_TSInteraction.attachmentIds as "Attachment",
        CASE
            when recordType is "9" then "Security Number Change"
            when recordType is "10" then "Contact changed name/joined Signal"
            when recordType is "13" then "Contact marked as verified"
            when recordType is "19" then "Incoming Message"
            when recordType is "20" then "Outgoing or Incoming call"
            when recordType is "21" then "Outgoing Message"
            when recordType is "28" then "Burn-On-Read timer changed"
            else recordType
            end "Record Type",
        model_TSInteraction.uniqueThreadId, 
        CASE
            when read is NULL then ""
            when read is "1" then "Yes"
            end "Read",
        errorType,
        offerType,
        infoMessageUserInfo
        from model_TSInteraction
        order by uniqueThreadId, timestamp
        """
    df = pd.read_sql_query(messagesQuery, conn)
    df = df[df.errorType.isnull()]
    df = df.drop(columns=['errorType'])
    
    getOfferType_iOS(df)
    df = df.drop(columns=['offerType', 'infoMessageUserInfo'])

    getAttachments_iOS(df, attachmentPath)

    pd.set_option('display.max_colwidth', None)

    for uniqueThreadId, df_uniqueThreadId in df.groupby('uniqueThreadId'):

        html =  html + df_uniqueThreadId.to_html(classes = 'table-striped', escape=False, col_space=100, justify='center', index=False, formatters=dict(
        Attachment=path_to_image_html))

    getContacts_iOS(db)


def path_to_image_html(path):
    global attachmentPath_relative
    global exe_path
    global outputDir_name
    global os_version
    try:
        path = path.replace("\\", "/")
    except Exception:
        pass
    if path:
        try:
            basename = ntpath.basename(path)
            path_with_output = outputDir_name + path[1:]
            if os_version == "ios":
                realpath = os.path.abspath(path_with_output)
            else:
                realpath = os.path.realpath(path)
                p = pathlib.Path(path)
                p = p.relative_to(*p.parts[:5])
                p = "./"+str(p)
                path = p
            if path == exe_path or path == "":
                return ""
            if path == "No support for this filetype":
                return "No support for this filetype"
            return ('<a href="file:///' + realpath + '"><img src="' + path + '" width="150" ><br>'+basename+'</a>')
        except:
            return "missing attachment"
    else:
        return ""

def getAttachments_iOS(df, attachmentPath):
    global outputDir_name
    attachmentPath = f"./{outputDir_name}/Attachments"
    result = list(Path(attachmentPath).rglob("*.*"))
    support = 0

    for index, row in df.iterrows():
        data = re.findall(
            "[A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{12}", str(row["Attachment"]))
        if data:
            support = 0
            for image in result:
                if data[0] in str(image):
                    data2 = str(image)
                    p = pathlib.Path(data2)
                    p = p.relative_to(*p.parts[:1])
                    p = "./"+str(p)
                    data2 = p
                    df.loc[index, "Attachment"] = data2
                    support = 1
            if support != 1:
                df.loc[index, "Attachment"] = "Error displaying attachment"
        else:
            df.loc[index, "Attachment"] = ""
            
def getOfferType_iOS(df):
    
    for index, row in df.iterrows():
        if row["offerType"] == 1:
            callType = row["Call Type"]
            df.loc[index, "Call Type"] = f"{callType} (Video Call)"
            

def getContacts_iOS(db):
    global html

    db_path = os.path.dirname(os.path.realpath(db))
    conn = sqlite3.connect(db)
    messagesQuery = """select 
        profileName as "Profile Name",
        CASE recipientPhoneNumber when "kLocalProfileUniqueId" then "Local User" else recipientPhoneNumber end "Phone Number",
        datetime(lastFetchDate, 'unixepoch') as "Last Fetch Date",
        datetime(lastMessagingDate, 'unixepoch') as "Last Messaging Date"
        from model_OWSUserProfile
        """
    df = pd.read_sql_query(messagesQuery, conn)
    
    html = html + df.to_html(classes = 'table-striped', escape=False, col_space=200, justify='center', index=False)

def windows(db, attachmentPath):

    global html
    print("Creating report")
    db_path = os.path.dirname(os.path.realpath(db))
    
    conn = sqlite3.connect(db)
    messagesQuery = """select    
        json,
        datetime(sent_at/1000, 'unixepoch') as "Sent At (UTC+0)", 
        datetime(received_at/1000, 'unixepoch') as "Received At (UTC+0)",
        conversationId,
        type
        from messages
        where type = 'incoming' or type = 'outgoing'
        order by conversationId, "Sent At (UTC+0)" 
        """
    acceptedTypes = ["incoming", "outgoing", "call-history"]
    df = pd.read_sql_query(messagesQuery, conn)
    df = df[df["type"].isin(acceptedTypes) == True]
    df_json = getJson_windows(df)
    df = df.drop(columns=["json"])
    
    if attachmentPath != "":
        getAttachment_windows(df_json, attachmentPath)
        
    df_json = df_json.rename(columns={'attachments': 'Attachment'})                               #Rename columns to look like iOS html report
    df["Attachment"] = df_json["Attachment"].values
    df["Sender"] = df_json["source"].values
    df["SourceUuid"] = df_json["sourceUuid"].values
    df["Body"] = df_json["body"].values
    

    df = df[['Sender', 'Received At (UTC+0)', 'Sent At (UTC+0)', 'Body', 'Attachment', 'type', 'conversationId']]

    for uniqueThreadId, df_uniqueThreadId in df.groupby('conversationId'):

        html =  html + df_uniqueThreadId.to_html(classes = 'table-striped', escape=False, col_space=100, justify='center', index=False, formatters=dict(
        Attachment=path_to_image_html))
        
    getContacts_windows(db)

def getJson_windows(df):

    json_string = "{"
    for index, row in df.iterrows():
        if index == 0:
            json_string = json_string + '"' + str(index) + '":' + row["json"]
        else:
            json_string = json_string + ", " + '"' + str(index) + '":' + row["json"]
    json_string = json_string + "}"

    with open("messages.json", "w", encoding="UTF-8") as f:
        f.write(json_string)

    a_json = json.loads(json_string)
    df = pd.DataFrame.from_dict(a_json, orient="index")
    
    os.remove("messages.json")

    return df


def getAttachment_windows(df, attachment_path):
        

    for index, row in df.iterrows():
        full_path = ""
        if len(row["attachments"]) != 0:
            item = row["attachments"]
            item = item[0]

            contentType = item['contentType']
            contentType = contentType.split("/")[1]
            if contentType == "plain":
                contentType = "txt"

            path = item['path']
            full_path = attachment_path + "\\" + path + "." + contentType
            try:
                os.rename(attachment_path + "\\" + path, attachment_path + "\\" + path + "." + contentType)
            except FileNotFoundError:
                pass
   
        if row["sticker"] is not None:
            sticker = row["sticker"]
            try:
                if math.isnan(sticker) == True:
                    df.loc[index, "attachments"] = ""
                    continue
            except:
                pass
            stickerItem = sticker['data']
            contentType = stickerItem['contentType']
            contentType = contentType.split("/")[1]
            if contentType == "plain":
                contentType = "txt"

            path = stickerItem['path']
            full_path = attachment_path + "\\" + path + "." + contentType
            try:
                os.rename(attachment_path + "\\" + path, attachment_path + "\\" + path + "." + contentType)
            except FileNotFoundError:
                pass
        try:
            if full_path != "":
                df.loc[index, "attachments"] = attachment_path + "\\" + path + "." + contentType
            else:
                df.loc[index, "attachments"] = ""
        except:
            pass
            
def getContacts_windows(db):
    global html

    db_path = os.path.dirname(os.path.realpath(db))
    conn = sqlite3.connect(db)
    messagesQuery = """
    select
    CASE
    when profileFullName is NULL then name
    else profileFullName
    END as "Profile Name",
    e164 as "Phone Number",
    datetime(active_at, 'unixepoch') as "Last Active Date",
    id as conversationId
    from conversations
    """

    df = pd.read_sql_query(messagesQuery, conn)


    html = html + df.to_html(classes = 'table-striped', escape=False, col_space=200, justify='center', index=False)

def main(db, os_version1, attachmentPath):
    global os_version
    global attachmentPath_relative
    global outputDir
    global outputDir_name
    os_version = os_version1
    print("OS VERSION", os_version)
    print("DATABASE", db)
    print("ATTACHMENT PATH", attachmentPath)
    print("")
    
    db_path = os.path.dirname(db)
    outputDir = db_path + "/" + "Signal_report" + '_' + datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
    outputDir_name = os.path.basename(outputDir)

    try:
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
    except ValueError:
        print("Could not create outdirectory")
        os.system("pause")
        sys.exit()
    if attachmentPath != "":
        copy_tree(attachmentPath, outputDir+"//Attachments")
        attachmentPath = outputDir+"//Attachments"
        attachmentPath_relative = "//Attachments"
    
    if os_version == "ios":
        iOS(db, attachmentPath)
    else:
        windows(db, attachmentPath)

    # write html to file
    text_file = open(f"{outputDir}/report_{os_version}.html", "w", encoding="utf-8")
    text_file.write(html)
    text_file.close()
    
    print(f"Report created, {outputDir}/report_{os_version}.html")
    os.system("pause")
    
if __name__ == '__main__':
    print(sys.argv[1:])
    main(sys.argv[1], sys.argv[2], sys.argv[3])
    
    