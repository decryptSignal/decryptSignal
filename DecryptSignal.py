import PySimpleGUI as sg
import sys
import os
import plistlib
from pysqlcipher3 import dbapi2 as sqlcipher
import report
import json

os_version = ""

def main_menu():
    global os_version
    global attachmentPath
    layout = [
        [sg.Text('Choose database source Operating System')],
        [sg.Radio("iOS", "os_input", default=True, key="ios"),
         sg.Radio("Windows", "os_input", default=False, key="windows")],
        [sg.Checkbox("Attachments", key="attachments_input")],
        [sg.Button("Auto"), sg.Button("Manual"), sg.Button("Cancel")]]

    window = sg.Window('Choose database source Operating System', layout)
    event, values = window.read()
    window.close()

    if event == "Cancel":
        sys.exit()
    
    mode = event
    os_version = values
    if values["attachments_input"]:
        attachmentPath = choose_attachments_path()
    else:
        attachmentPath = ""
    if values["ios"]:
        os_version = "ios"
        if mode == "Auto":
            decryptedDB = ios_auto()
        else:
            decryptedDB = ios()
    elif values["windows"]:
        os_version = "windows"
        if mode == "Auto":
            decryptedDB = windows_auto()
        else:
            decryptedDB = windows()

    return decryptedDB


def ios_auto():
    print("RUNNING IOS AUTO\n")
    encryptedDB = "signal.sqlite"
    keychainDump = ""
    DB_found = False
    error = False

    for file_name in os.listdir(os.path.dirname(os.path.realpath(__file__))):
        if file_name == encryptedDB:
            DB_found = True
        if file_name.endswith("signal.json") or file_name.endswith("keychain.plist"):
            keychainDump = file_name

    if not DB_found:
        print(f"Could not find {encryptedDB}, check that the file is in the same folder as the script or run script in "
              f"Manual mode")
        error = True
    if keychainDump == "":
        print("Could not find keychain file, rename your keychain file to 'signal.json' or run script in Manual "
              "mode")
        error = True
    if error:
        os.system("pause")
        sys.exit()

    encryptedDB = os.path.realpath(encryptedDB)
    keychainDump = os.path.realpath(keychainDump)

    decryptedDB = decrypt_ios(encryptedDB, keychainDump)

    return decryptedDB


def ios():
    print("RUNNING IOS MANUAL\n")
    layout = [
        [sg.Text("Signal database")],
        [sg.In(key="database_input"), sg.FileBrowse(target="database_input", initial_folder=sys.path[0])],

        [sg.Text('Keychain file')],
        [sg.In(key="keychain_input"), sg.FileBrowse(target="keychain_input", initial_folder=sys.path[0])],

        [sg.Button("Ok"), sg.Button("Cancel")]]

    window = sg.Window('Choose values', layout)
    event, values = window.read()
    window.close()

    if event == "Cancel":
        sys.exit()

    encryptedDB = ""
    keychainDump = ""

    try:
        encryptedDB = values["database_input"]
        keychainDump = values["keychain_input"]
    except KeyError as E:
        print(E)

    if encryptedDB == "":
        print("No database chosen, exiting")
        os.system("pause")
        sys.exit()
    elif keychainDump == "":
        print("No keychain chosen, exiting")
        os.system("pause")
        sys.exit()

    print("Signal database:", encryptedDB)
    print("Keychain file:", keychainDump)

    decryptedDB = decrypt_ios(encryptedDB, keychainDump)

    return decryptedDB


def windows_auto():
    print("RUNNING WINDOWS AUTO\n")
    encryptedDB = "db.sqlite"
    configfile = "config.json"
    DB_found = False
    config_found = False
    error = False

    for file_name in os.listdir(os.path.dirname(os.path.realpath(__file__))):
        if file_name == encryptedDB:
            DB_found = True
        if file_name == configfile:
            config_found = True

    if not DB_found:
        print(f"Could not find {encryptedDB}, check that the file is in the same folder as the script or run script in "
              f"Manual mode")
        error = True
    if not config_found:
        print(f"Could not find {configfile}, check that the file is in the same folder as the script or run script in "
              f"Manual mode")
        error = True
    if error:
        os.system("pause")
        sys.exit()

    encryptedDB = os.path.realpath(encryptedDB)
    configfile = os.path.realpath(configfile)

    decryptedDB = decrypt_windows(encryptedDB, configfile)

    return decryptedDB


def windows():
    print("RUNNING WINDOWS\n")
    layout = [
        [sg.Text("Signal database")],
        [sg.In(key="database_input"), sg.FileBrowse(target="database_input", initial_folder=sys.path[0])],

        [sg.Text('Config file')],
        [sg.In(key="config_input"), sg.FileBrowse(target="config_input", initial_folder=sys.path[0])],

        [sg.Button("Ok"), sg.Button("Cancel")]]

    window = sg.Window('Choose values', layout)
    event, values = window.read()
    window.close()

    if event == "Cancel":
        sys.exit()

    encryptedDB = ""
    configfile = ""

    try:
        encryptedDB = values["database_input"]
        configfile = values["config_input"]
    except KeyError as E:
        print(E)

    if encryptedDB == "":
        print("No database chosen, exiting")
        os.system("pause")
        sys.exit()
    elif configfile == "":
        print("No keychain chosen, exiting")
        os.system("pause")
        sys.exit()

    print("Signal database:", encryptedDB)
    print("Keychain file:", configfile)

    decryptedDB = decrypt_windows(encryptedDB, configfile)

    return decryptedDB


def decrypt_ios(encryptedDB, keychainDump):
    print("Decrypting database")

    key = get_ios_db_key(keychainDump)
    print("Database key =", key, "\n")

    decryptedDB = decrypt_db(encryptedDB, key, "ios")
    print("Decrypted database name:", decryptedDB)

    return decryptedDB


def decrypt_windows(encryptedDB, configfile):
    print("Decrypting database")

    with open(configfile) as f:
        config_data = json.load(f)

    key = config_data["key"]
    print("Database key =", key, "\n")

    decryptedDB = decrypt_db(encryptedDB, key, "windows")
    print("Decrypted database name:", decryptedDB)

    return decryptedDB


def get_ios_db_key(keychainDump):
    try:
        with open(keychainDump, 'rb') as f:
            keychain_plist = plistlib.load(f)
            for x in keychain_plist.values():
                for y in x:
                    if 'agrp' in y.keys():
                        if y['agrp'] == b'U68MSDN6DR.org.whispersystems.signal' or \
                                y['agrp'] == "U68MSDN6DR.org.whispersystems.signal":
                            if y['acct'] == b'GRDBDatabaseCipherKeySpec' or y['acct'] == 'GRDBDatabaseCipherKeySpec':
                                key = y['v_Data'].hex()
    except:
        with open(keychainDump, 'rb') as f:
            json_data = json.load(f)
            json_data = json_data[0]
            key = json_data["dataHex"]
    return key


def decrypt_db(db, key, operating_system):
    plaintextDB = os.path.splitext(db)[0] + "_decrypted.sqlite"
    conn = sqlcipher.connect(db)
    cur = conn.cursor()
    if os.path.exists(plaintextDB):
        print("Decrypted database %s already exists in destination folder. Delete it and run again." % plaintextDB)
        os.system("pause")
        sys.exit()
    print("Decrypting database...")
    cur.execute('PRAGMA key="x\'' + key + '\'"')
    if operating_system == "ios":
        cur.execute('PRAGMA cipher_plaintext_header_size = 32')
    try:
        cur.execute('SELECT count(*) FROM sqlite_master')
    except sqlcipher.DatabaseError as E:
        print("Decryption failed\nError:", E)
        os.system("pause")
        sys.exit()
    cur.execute('ATTACH DATABASE "' + plaintextDB + '" AS plaintext KEY ""')
    cur.execute('SELECT sqlcipher_export("plaintext")')
    cur.execute('DETACH DATABASE plaintext')
    print("Decryption complete")
    conn.commit()
    cur.close()

    return plaintextDB
    
def choose_attachments_path():

    layout = [
            [sg.Text('Choose attachment folder')],
            [sg.In(key="attachments_path_input"), sg.FolderBrowse(target="attachments_path_input")],
            [sg.Button('Ok'), sg.Button('Cancel')]]
            
    window = sg.Window('Choose attachments folder', layout)
    event, values = window.read()
    window.close()
    
    if event == "Cancel":
        sys.exit()
    else:
        attachments_path = values['attachments_path_input']
        
    return attachments_path


def main():
    global os_version
    global attachmentPath
    decryptedDB = main_menu()
    report.main(decryptedDB, os_version, attachmentPath)


if __name__ == '__main__':
    main()
