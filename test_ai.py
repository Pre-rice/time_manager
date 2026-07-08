import urllib.request, json  
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=json.dumps({'username':'testdemo','password':'123456'}).encode(), headers={'Content-Type':'application/json'})  
token = json.loads(urllib.request.urlopen(req).read())['access_token']  
print('登录成功')  
req = urllib.request.Request('http://localhost:8000/api/v1/ai/config/', headers={'Authorization':f'Bearer {token}'})  
try: data = json.loads(urllib.request.urlopen(req).read())  
print('AI配置:', data)  
except Exception as e: print('无AI配置:', e)  
req = urllib.request.Request('http://localhost:8000/api/v1/ai/extract', data=json.dumps({'text':'明天下午3点开会'}).encode(), headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}, method='POST')  
try:  
  resp = urllib.request.urlopen(req)  
  print('提取结果:', resp.read().decode())  
except urllib.error.HTTPError as e:  
  print('提取失败:', e.code, e.read().decode())  
