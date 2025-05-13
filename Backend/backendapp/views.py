from django.http.response import JsonResponse
from django.shortcuts import render
from datetime import datetime
from django.http import JsonResponse
import json
from neo4j import GraphDatabase
from django.views.decorators.csrf import csrf_exempt
from Backend.settings import sendMail, sendResponse ,disconnectDB, connectDB, resultMessages, generateStr, execute_query

# Odoogiin tsagiig duuddag service
def dt_gettime(request):
    jsons = json.loads(request.body) # request body-g dictionary bolgon avch baina
    action = jsons["action"] #jsons-s action-g salgaj avch baina
    

    
    respdata = [{'time':datetime.now().strftime("%Y/%m/%d, %H:%M:%S")}]  # response-n data-g beldej baina. list turultei baih
    resp = sendResponse(request, 200, respdata, action)
    # response beldej baina. 6 keytei.
    return resp
# dt_gettime

#login service
def dt_login(request):
    jsons = json.loads(request.body)
    action = jsons['action']
    # url: http://localhost:8000/user/
    # Method: POST
    # Body: raw JSON
    
    # request body:
    # {
    #     "action": "login",
    #     "uname": "ganzoo@mandakh.edu.mn",
    #     "upassword":"73y483h4bhu34buhrbq3uhbi3aefgiu"
    # }
    
    # response:
    # {
    #     "resultCode": 1002,
    #     "resultMessage": "Login Successful",
    #     "data": [
    #         {
    #             "uname": "ganzoo@mandakh.edu.mn",
    #             "fname": "Ganzo",
    #             "lname": "U",
    #             "lastlogin": "2024-11-06T15:57:52.996+08:00"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "login",
    #     "curdate": "2024/11/06 07:58:10"
    # }
    try:
        uname = jsons['uname'].lower()
        upassword = jsons['upassword']
    except KeyError:
        respdata = []
        resp = sendResponse(request, 3006, respdata, action)
        return resp

    try:
        driver = connectDB()

        # Verify user credentials
        query = (
            "MATCH (u:User) "
            "WHERE u.uname = $uname AND u.upassword = $upassword AND u.isverified = true AND u.isbanned = false "
            "RETURN COUNT(u) AS usercount, u.fname AS fname, u.lname AS lname"
        )
        result = execute_query(driver, query, {"uname": uname, "upassword": upassword})

        if result and result[0]["usercount"] == 1:
            # Fetch user details
            query = (
                """MATCH (u:User) 
                WHERE u.uname = $uname AND u.upassword = $upassword 
                RETURN id(u) AS uid, u.uname AS uname, u.fname AS fname, u.lname AS lname"""
            )
            user_data = execute_query(driver, query, {"uname": uname, "upassword": upassword})[0]
            print(user_data)
            # Update last login
            query = (
                """MATCH (u:User) 
                WHERE u.uname = $uname AND u.upassword = $upassword 
                SET u.lastlogin = datetime()"""
            )
            execute_query(driver, query, {"uname": uname, "upassword": upassword})

            respdata = [user_data]
            resp = sendResponse(request, 1002, respdata, action)
        else:
            respdata = [{"uname": uname}]
            resp = sendResponse(request, 1004, respdata, action)
    except Exception as e:
        respdata = []
        resp = sendResponse(request, 5001, respdata, action)
    finally:
        disconnectDB(driver)
        return resp
#dt_login

def dt_register(request):
    jsons = json.loads(request.body) # get request body
    action = jsons["action"] # get action key from jsons
    # print(action)
    
    # url: http://localhost:8000/user/
    # Method: POST
    # Body: raw JSON
    
    # request body:
    # {
    #     "action": "register",
    #     "uname": "ganzoo@mandakh.edu.mn",
    #     "upassword":"a9b7ba70783b617e9998dc4dd82eb3c5",
    #     "lname":"Ganzo",
    #     "fname":"U"
    # }
    
    # response:
    # {
    #     "resultCode": 200,
    #     "resultMessage": "Success",
    #     "data": [
    #         {
    #             "uname": "ganzoo@mandakh.edu.mn",
    #             "lname": "U",
    #             "fname": "Ganzo"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "register",
    #     "curdate": "2024/11/06 07:59:23"
    # }

    try:
        uname = jsons["uname"].lower()
        lname = jsons["lname"].capitalize()
        fname = jsons["fname"].capitalize()
        upassword = jsons["upassword"]
    except KeyError:
        respdata = []
        resp = sendResponse(request, 3007, respdata, action)
        return resp

    try:
        driver = connectDB()

        # Check if user already exists
        query = "MATCH (u:User {uname: $uname, isverified: true}) RETURN COUNT(u) AS usercount"
        result = execute_query(driver, query, {"uname": uname})

        if result and result[0]["usercount"] == 0:
            # Create new user
            query = (
                "CREATE (u:User {uname: $uname, lname: $lname, fname: $fname, upassword: $upassword, "
                "isverified: false, isbanned: false, createddate: datetime(), lastlogin: datetime('1970-01-01')}) "
                "RETURN id(u) AS uid"
            )
            user_result = execute_query(driver, query, {
                "uname": uname,
                "lname": lname,
                "fname": fname,
                "upassword": upassword,
            })

            uid = user_result[0]["uid"]

            # Generate token and save to the database
            token = generateStr(20)
            query = (
                "CREATE (t:Token {uid: $uid, token: $token, tokentype: 'register', "
                "tokenenddate: datetime() + duration({days: 1}), createddate: datetime()})"
            )
            execute_query(driver, query, {"uid": uid, "token": token})

            # Send verification email
            subject = "User Registration Confirmation"
            bodyHTML = F"""<a target='_blank' href=http://localhost:8000/user?token={token}>CLICK ME</a>"""
            sendMail(uname, subject, bodyHTML)

            respdata = [{"uid" : uid,"uname": uname, "lname": lname, "fname": fname}]
            resp = sendResponse(request, 200, respdata, action)
        else:
            respdata = [{"uname": uname, "fname": fname}]
            resp = sendResponse(request, 3008, respdata, action)
    except Exception as e:
        respdata = [{"error": str(e)}]
        resp = sendResponse(request, 5002, respdata, action)
    finally:
        disconnectDB(driver)
        return resp

# dt_register

# Nuuts ugee martsan bol duudah service
def dt_forgot(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # print(action)
    resp = {}
    
    # url: http://localhost:8000/user/
    # Method: POST
    # Body: raw JSON
    
    # request body:
    # {
    #     "action": "forgot",
    #     "uname": "ganzoo@mandakh.edu.mn"
    # }
    
    # response: 
    # {
    #     "resultCode": 3012,
    #     "resultMessage": "Forgot password huselt ilgeelee",
    #     "data": [
    #         {
    #             "uname": "ganzoo@mandakh.edu.mn"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "forgot",
    #     "curdate": "2024/11/06 08:00:32"
    # }
    try:    
        uname = jsons['uname'].lower() # get uname key from jsons
    except: # uname key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 3016, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB()

        # Check if the user exists and is verified
        query = """
            MATCH (u:User {uname: $uname, isverified: true})
            RETURN u.uname AS uname, u.uid AS uid
        """
        result = execute_query(driver, query, {"uname": uname})
        
        if result:
            uid = result[0]["uid"]
            uname = result[0]["uname"]

            # Generate a token for password reset
            token = generateStr(25)
            token_query = """
                CREATE (t:Token {
                    uid: $uid, token: $token, tokentype: 'forgot',
                    tokenenddate: datetime() + duration({days: 1}), createddate: datetime()
                })
            """
            execute_query(driver, token_query, {"uid": uid, "token": token})

            # Send password reset email
            reset_link = f"http://localhost:8000/user?token={token}"
            subject = "Nuuts ug shinechleh"
            bodyHTML = f"<a href='{reset_link}'>Martsan nuuts ugee shinechleh link</a>"
            sendMail(uname, subject, bodyHTML)

            # Return success response
            respdata = [{"uname": uname}]
            resp = sendResponse(request,3012,respdata,action )
        
        else: # verified user not found 
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request,3013,respdata,action )
            
    except Exception as e: # forgot service deer dotood aldaa garsan bol ajillana.
        # forgot service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 5003, respdata, action) # standartiin daguu 6 key-tei response butsaana
    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina
# dt_forgot

# Nuuts ugee martsan uyd resetpassword service-r nuuts ugee shinechilne
def dt_resetpassword(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # print(action)
    resp = {}
    
    # url: http://localhost:8000/user/
    # Method: POST
    # Body: raw JSON
    
    # request body:
    #  {
    #     "action": "resetpassword",
    #     "token":"145v2n080t0lqh3i1dvpt3tgkrmn3kygqf5sqwnw",
    #     "newpass":"MandakhSchool"
    # }
    
    # response:
    # {
    #     "resultCode": 3019,
    #     "resultMessage": "martsan nuuts ugiig shinchille",
    #     "data": [
    #         {
    #             "uname": "ganzoo@mandakh.edu.mn"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "resetpassword",
    #     "curdate": "2024/11/06 08:03:25"
    # }
    try:
        newpass = jsons['newpass'] # get newpass key from jsons
        token = jsons['token'] # get token key from jsons
    except: # newpass, token key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 3018, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB() # database holbolt uusgej baina
        
        # Tuhain token deer burtgeltei batalgaajsan hereglegch baigaa esehiig shalgana. Neg l hereglegch songogdono esvel songogdohgui. Token buruu, hugatsaa duussan bol resetpassword service ajillahgui.
        query = f"""
            MATCH (u:User)-[:HAS_TOKEN]->(t:Token)
            WHERE t.token = $token
            AND u.isverified = true
            AND t.tokenenddate > datetime()
            RETURN u.uname AS uname, u.uid AS uid, t.tokenid AS tokenid
            """
        result = execute_query(driver, query, {"token": token})
        
        if result: # token idevhtei, verified hereglegch oldson bol nuuts ugiig shinechlehiig zuvshuurnu.
            uid = result[0]["uid"]
            uname = result[0]["uname"]
            tokenid = result[0]["tokenid"]
            new_token = generateStr(40)  # Generate new token
            
            query = """
                MATCH (u:User {uid: $uid})
                SET u.upassword = $newpass
                """ # Updating user's new password in t_user
            execute_query(driver, query, {"uid": uid, "newpass": newpass})
            
            token_update_query = """
                MATCH (t:Token {tokenid: $tokenid})
                SET t.token = $new_token, t.tokenenddate = datetime("1970-01-01T00:00:00")
            """
            execute_query(driver, token_update_query, {"tokenid": tokenid, "new_token": new_token})
            # sending Response
            
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request,3019,respdata,action )
            
        else: # token not found 
            action = jsons['action']
            respdata = []
            resp = sendResponse(request,3020,respdata,action )
            
    except Exception as e: # reset password service deer dotood aldaa garsan bol ajillana.
        # reset service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # aldaanii medeelel bustaana.
        resp = sendResponse(request, 5005, respdata, action) # standartiin daguu 6 key-tei response butsaana
    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina
#dt_resetpassword

# Huuchin nuuts ugee ashiglan Shine nuuts ugeer shinechleh service
def dt_changepassword(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # print(action)
    resp = {}
    
    # url: http://localhost:8000/user/
    # Method: POST
    # Body: raw JSON
    
    # request body:
    # {
    #     "action": "changepassword",
    #     "uname": "ganzoo@mandakh.edu.mn",
    #     "oldpass":"a1b2c3d4",
    #     "newpass":"a1b2"
    # }
    
    # response: 
    # {
    #     "resultCode": 3022,
    #     "resultMessage": "nuuts ug amjilttai soligdloo ",
    #     "data": [
    #         {
    #             "uname": "ganzoo@mandakh.edu.mn",
    #             "lname": "U",
    #             "fname": "Ganzo"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "changepassword",
    #     "curdate": "2024/11/06 08:04:18"
    # }
    try:
        uname = jsons['uname'].lower() # get uname key from jsons
        newpass = jsons['newpass'] # get newpass key from jsons
        oldpass = jsons['oldpass'] # get oldpass key from jsons
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 3021, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB() # database holbolt uusgej baina
        # burtgeltei batalgaajsan hereglegchiin nuuts ug zuv esehiig shalgaj baina. Burtgelgui, verified hiigeegui, huuchin nuuts ug taarahgui hereglegch bol change password ajillahgui.
        query = """
            MATCH (u:User)
            WHERE u.uname = $uname AND u.isverified = true AND u.upassword = $oldpass
            RETURN u.uname AS uname, u.uid AS uid, u.lname AS lname, u.fname AS fname
        """
        result = execute_query(driver, query, {"uname": uname, "oldpass": oldpass})


        if result:  # If the user is found and the old password matches
            uid = result[0]["uid"]
            uname = result[0]["uname"]
            lname = result[0]["lname"]
            fname = result[0]["fname"]
            
            password_update_query = """
                MATCH (u:User {uid: $uid})
                SET u.upassword = $newpass
            """
            execute_query(driver, password_update_query, {"uid": uid, "newpass": newpass})

            # sending Response
            action = jsons['action']
            respdata = [{"uname":uname, "lname": lname, "fname":fname}]
            resp = sendResponse(request, 3022, respdata, action )
            
        else: # old password not match
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request, 3023, respdata, action )
            
    except Exception as e: # change password service deer dotood aldaa garsan bol ajillana.
        # change service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 5006, respdata, action) # standartiin daguu 6 key-tei response butsaana
    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina
# dt_changepassword

def dt_add_tem(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # {
    #     "action": "diaryadd",
    #     "uname": "sw22d027@mandakh.edu.mn",
    #     "title":"test1",
    #     "diary":"Unuudur 2025 onii 1 sariin 1 nii 1:tsag 5 minut"
    # }
    # {
    #     "resultCode": 4001,
    #     "resultMessage": "Temdeglel amjilttai nemegdlee",
    #     "data": [
    #         {
    #             "uname": "sw22d027@mandakh.edu.mn"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "diaryadd",
    #     "curdate": "2025/01/01 01:05:50"
    # }
    try:
        uname = jsons['uname'].lower() # get uname key from jsons
        title = jsons['title'] # get newpass key from jsons
        diary = jsons['diary'] # get oldpass key from jsons
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 4006, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB() # database holbolt uusgej baina
        # burtgeltei batalgaajsan hereglegchiin nuuts ug zuv esehiig shalgaj baina. Burtgelgui, verified hiigeegui, huuchin nuuts ug taarahgui hereglegch bol change password ajillahgui.
        query = """
            MATCH (u:User)
            WHERE u.uname = $uname AND u.isverified = true 
            RETURN id(u) as uid
        """
        result = execute_query(driver, query, {"uname": uname})
        if result:
            now = str(datetime.now())
            now = now.split(".")[0]
            query1 = """
                MATCH (u:User)
                WHERE u.uname = $uname AND u.isverified = true
                CREATE (d:Diary { title: $title, diary: $diary, date: $date })-[:DIARY]->(u)
                RETURN id(u) AS uid 
            """
            result = execute_query(driver, query1, {"uname": uname, "title" : title, "diary" : diary, "date" : now})
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request, 4001, respdata, action )
        else:
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request, 4002, respdata, action )
            
    except Exception as e: # change password service deer dotood aldaa garsan bol ajillana.
        # change service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 4003, respdata, action) # standartiin daguu 6 key-tei response butsaana

    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina
    
    
def dt_editdiary(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # request body:
    # {
    #     "action": "diaryedit",
    #     "uname": "sw22d027@mandakh.edu.mn",
    #     "did": 2,
    #     "title" : "aaa",
    #     "diary" : "dd",
    # }
    
    # {
    #     "resultCode": 4004,
    #     "resultMessage": "title diary amjilttai soligdloo",
    #     "data": [
    #         {
    #             "uname": "sw22d027@mandakh.edu.mn"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "diaryedit",
    #     "curdate": "2025/01/01 01:34:30"
    # }
    try:
        uname = jsons['uname'].lower() # get uname key from jsons
        did = jsons['did']
        title = jsons['title'] # get title key from jsons
        diary = jsons['diary'] # get diary key from jsons
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 4007, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB() # database holbolt uusgej baina
        # burtgeltei batalgaajsan hereglegchiin nuuts ug zuv esehiig shalgaj baina. Burtgelgui, verified hiigeegui, huuchin nuuts ug taarahgui hereglegch bol change password ajillahgui.
        query = """
            MATCH (u:User)
            WHERE u.uname = $uname AND u.isverified = true 
            RETURN id(u) as uid
        """
        result = execute_query(driver, query, {"uname": uname})
        if result:
            URI = 'bolt://localhost:7687'
            AUTH = ('neo4j', '20041218')
            with GraphDatabase.driver(uri= URI, auth= AUTH) as con:
                rows , summary, keys = con.execute_query(f"""
                MATCH (d:Diary)
                WHERE id(d) = {did}
                SET d.title = '{title}', d.diary = '{diary}'
                RETURN id(d) AS uid, d.title as title
                """)
            action = jsons['action']    
            respdata = [{"uname":uname}]
            resp = sendResponse(request, 4004, respdata, action )
        else:
            action = jsons['action']
            respdata = [{"uname":uname}]
            resp = sendResponse(request, 4002, respdata, action )
            
    except Exception as e: # change password service deer dotood aldaa garsan bol ajillana.
        # change service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 4005, respdata, action) # standartiin daguu 6 key-tei response butsaana

    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina


def dt_deletediary(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # request body:
    # {
    #     "action": "deletediary",
    #     "uname": "sw22d027@mandakh.edu.mn",
    #     "did": 2,
    # }
    
    # {
    #     "resultCode": 4005,
    #     "resultMessage": "Temdeglel amjilttai nemegdlee",
    #     "data": [
    #         {
    #             "uname": "sw22d027@mandakh.edu.mn"
    #         }
    #     ],
    #     "size": 1,
    #     "action": "diaryadd",
    #     "curdate": "2025/01/01 01:05:50"
    # }
    try:
        uname = jsons['uname'].lower() # get uname key from jsons
        did = jsons['did']
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 4008, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        URI = 'bolt://localhost:7687'
        AUTH = ('neo4j', '20041218')
        with GraphDatabase.driver(uri= URI, auth= AUTH) as con:
            rows , summary, keys = con.execute_query(f"""
            MATCH (d:Diary)
            WHERE id(d) = {did} 
            DETACH DELETE d
            """)
        action = jsons['action']
        respdata = [{"uname":uname}]
        resp = sendResponse(request, 4009, respdata, action )
    except Exception as e: # change password service deer dotood aldaa garsan bol ajillana.
        # change service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 4010, respdata, action) # standartiin daguu 6 key-tei response butsaana

    finally:
        # disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina




def dt_getdiary(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # request body:
    # {
    #     "action": "getdiary",
    #     "uname": "sw22d027@mandakh.edu.mn",
    # }
    
    # {
    #     "resultCode": 4012,
    #     "resultMessage": "amjilttai diary tatsan",
    #     "data": [
    #         {
    #             "did": 2,
    #             "title": "test"
    #         },
    #         {
    #             "did": 3,
    #             "title": "test1"
    #         }
    #     ],
    #     "size": 2,
    #     "action": "getdiary",
    #     "curdate": "2025/01/01 01:56:33"
    # }
    try:
        uid = jsons['uid'] # get uname key from jsons
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 4011, respdata, action) # response beldej baina. 6 keytei.
        return resp
    
    try: 
        driver = connectDB() # database holbolt uusgej baina
        # burtgeltei batalgaajsan hereglegchiin nuuts ug zuv esehiig shalgaj baina. Burtgelgui, verified hiigeegui, huuchin nuuts ug taarahgui hereglegch bol change password ajillahgui.
        query = """
            MATCH (u:User) <- [DIARY] - (d:Diary)
            WHERE id(u) = $uid
            RETURN id(d) as did , d.title as title, d.date as date
        """
        result = execute_query(driver, query, {"uid": uid})
        action = jsons['action']
        respdata = result
        resp = sendResponse(request, 4012, respdata, action )
    except Exception as e: 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 4013, respdata, action) # standartiin daguu 6 key-tei response butsaana

    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina


def dt_detaildiary(request):
    jsons = json.loads(request.body) # get request body
    action = jsons['action'] # get action key from jsons
    # request body:
    # {
    #     "action": "detaildiary",
    #     "uname": "sw22d027@mandakh.edu.mn",
    #     "did" : 2
    # }
    
    # {
    #     "resultCode": 4016,
    #     "resultMessage": "diary detail amjilttai",
    #     "data": [
    #         "sw22d027@mandakh.edu.mn",
    #         {
    #             "did": 2,
    #             "title": "test",
    #             "diary": "Unuudur 2025 onii 1 sariin 1 nii 1:tsag 2 minut"
    #         }
    #     ],
    #     "size": 2,
    #     "action": "detaildiary",
    #     "curdate": "2025/01/01 02:05:18"
    # }
    try:
        uname = jsons['uname'].lower() # get uname key from jsons
        did = jsons['did']
    except: # uname, newpass, oldpass key ali neg ni baihgui bol aldaanii medeelel butsaana
        action = jsons['action']
        respdata = []
        resp = sendResponse(request, 4014, respdata, action) # response beldej baina. 6 keytei.
        return resp

    try: 
        did = int(did)
        driver = connectDB() # database holbolt uusgej baina
        # burtgeltei batalgaajsan hereglegchiin nuuts ug zuv esehiig shalgaj baina. Burtgelgui, verified hiigeegui, huuchin nuuts ug taarahgui hereglegch bol change password ajillahgui.
        query = """
            MATCH (d:Diary) - [:DIARY] -> (u:User {uname: $uname})
            WHERE id(d) = $did
            RETURN id(d) AS did, d.title AS title, d.diary AS diary, d.date AS date
        """
        result = execute_query(driver, query, {"did": did, "uname": uname})
        action = jsons['action']
        respdata = result
        resp = sendResponse(request, 4016, respdata, action )
    except Exception as e: # change password service deer dotood aldaa garsan bol ajillana.
        # change service deer aldaa garval ajillana. 
        action = jsons["action"]
        respdata = [{"error":str(e)}] # hooson data bustaana.
        resp = sendResponse(request, 4015, respdata, action) # standartiin daguu 6 key-tei response butsaana

    finally:
        disconnectDB(driver) # yamarch uyd database holbolt uussen bol holboltiig salgana. Uchir ni finally dotor baigaa
        return resp # response bustaaj baina

@csrf_exempt  # Disable CSRF for this view
def checkService(request):
    if request.method == "POST":  # Handle POST requests
        try:
            jsons = json.loads(request.body)  # Parse request body to JSON
        except:
            action = "no action"
            respdata = []
            resp = sendResponse(request, 3003, respdata)
            return JsonResponse(resp)

        try:
            action = jsons["action"]  # Extract "action" from the JSON
        except:
            action = "no action"
            respdata = []
            resp = sendResponse(request, 3005, respdata, action)
            return JsonResponse(resp)

        # Routing based on "action"
        if action == "gettime":
            result = dt_gettime(request)
            return JsonResponse(result)
        elif action == "login":
            result = dt_login(request)
            return JsonResponse(result)
        elif action == "register":
            result = dt_register(request)
            return JsonResponse(result)
        elif action == "forgot":
            result = dt_forgot(request)
            return JsonResponse(result)
        elif action == "resetpassword":
            result = dt_resetpassword(request)
            return JsonResponse(result)
        elif action == "changepassword":
            result = dt_changepassword(request)
            return JsonResponse(result)
        elif action == "diaryadd":
            result = dt_add_tem(request)
            return JsonResponse(result)
        elif action == "diaryedit":
            result = dt_editdiary(request)
            return JsonResponse(result)
        elif action == "diarydelete":
            result = dt_deletediary(request)
            return JsonResponse(result)
        elif action == "getdiary":
            result = dt_getdiary(request)
            return JsonResponse(result)
        elif action == "detaildiary":
            result = dt_detaildiary(request)
            return JsonResponse(result)
        else:
            action = "no action"
            respdata = []
            resp = sendResponse(request, 3001, respdata, action)
            return JsonResponse(resp)

    elif request.method == "GET":  # Handle GET requests
        token = request.GET.get('token')
        if token is None:
            action = "no action"
            respdata = []
            resp = sendResponse(request, 3015, respdata, action)
            return JsonResponse(resp)

        try:
            driver = connectDB()  # Connect to Neo4j

            # Check if the token exists and is valid
            query = (
                "MATCH (t:Token {token: $token}) WHERE t.tokenenddate > datetime() "
                "RETURN id(t) AS tokenid, t.tokentype AS tokentype, t.uid AS uid"
            )
            result = execute_query(driver, query, {"token": token})

            if result:
                token_data = result[0]
                tokenid = token_data["tokenid"]
                tokentype = token_data["tokentype"]
                uid = token_data["uid"]

                if tokentype == "register":
                    # Check user information
                    query = (
                        """MATCH (u:User) where id(u) = $uid
                        RETURN u.uname AS uname, u.lname AS lname, u.fname AS fname, u.createddate AS createddate, u.isverified AS isverified"""
                    )
                    user_result = execute_query(driver, query, {"uid": uid})

                    if user_result:
                        user = user_result[0]
                        if not user["isverified"]:
                            # Verify user
                            update_query = "MATCH (u:User) where id(u) = $uid SET u.isverified = true"
                            execute_query(driver, update_query, {"uid": uid})

                            # Invalidate token
                            new_token = generateStr(30)
                            invalidate_query = (
                                "MATCH (t:Token {tokenid: $tokenid}) "
                                "SET t.token = $new_token, t.tokenenddate = datetime('1970-01-01')"
                            )
                            execute_query(driver, invalidate_query, {"tokenid": tokenid, "new_token": new_token})

                            action = "userverified"
                            respdata = [{
                                "uid": uid,
                                "uname": user["uname"],
                                "lname": user["lname"],
                                "fname": user["fname"],
                                "tokentype": tokentype,
                                "createddate": str(user["createddate"]),
                            }]
                            resp = sendResponse(request, 3010, respdata, action)
                        else:
                            action = "user verified already"
                            respdata = [{"uname": user["uname"], "tokentype": tokentype}]
                            resp = sendResponse(request, 3014, respdata, action)

                elif tokentype == "forgot":
                    # Handle forgot password token
                    query = (
                        "MATCH (u:User {uid: $uid}) WHERE u.isverified = true "
                        "RETURN u.uname AS uname, u.lname AS lname, u.fname AS fname, u.createddate AS createddate"
                    )
                    user_result = execute_query(driver, query, {"uid": uid})

                    if user_result:
                        user = user_result[0]
                        action = "forgot user verify"
                        respdata = [{
                            "uid": uid,
                            "uname": user["uname"],
                            "tokentype": tokentype,
                            "createddate": user["createddate"],
                        }]
                        resp = sendResponse(request, 3011, respdata, action)
                else:
                    action = "no action"
                    respdata = []
                    resp = sendResponse(request, 3017, respdata, action)
            else:
                action = "notoken"
                respdata = []
                resp = sendResponse(request, 3009, respdata, action)

        except Exception as e:
            action = "no action"
            respdata = [{"error": str(e)}]
            resp = sendResponse(request, 5004, respdata, action)
        finally:
            disconnectDB(driver)
            return JsonResponse(resp)

    else:  # Handle unsupported methods
        action = "no action"
        respdata = []
        resp = sendResponse(request, 3002, respdata, action)
        return JsonResponse(resp)
