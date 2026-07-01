import urllib.request, json
req = urllib.request.Request('http://localhost:8000/auth/login', data=b'username=admin&password=123', headers={'Content-Type': 'application/x-www-form-urlencoded'})
try:
    res = urllib.request.urlopen(req)
    cookie = res.info().get('Set-Cookie')
    req2 = urllib.request.Request('http://localhost:8000/auth/change-password', data=json.dumps({'old_password':'123','new_password':'123456'}).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
    try:
        res2 = urllib.request.urlopen(req2)
        print("OK", res2.read().decode())
    except Exception as e2:
        print("ERR2", e2)
        if hasattr(e2, 'read'): print(e2.read().decode('utf-8'))
except Exception as e:
    print("ERR1", e)
