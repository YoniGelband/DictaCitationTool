import requests
string = "היו שנים רוכבין על גבי בהמה או שהיה אחד [MASK] ואחד מנהיג"
berel_url = "http://54.213.196.28:8080/api"
model = "ckpt_34800"


body = {"data":string,"models":[model]}
res=requests.post(berel_url, json=body)
options = res.json()
#options = [r[model] for r in options if r][0]
print(options)