import requests

# provide a common interface for all request/compute/request challenges
def challenge(challenge_id, session_id, callback, delimiter="MESSAGE"):

    base_url = 'https://ringzer0team.com/challenges/{}/'
    cookies = dict(PHPSESSID=session_id)
    url = base_url.format(challenge_id)

    # First request: get the text
    try:
        r = requests.get(url, cookies=cookies)
        string = r.text \
                .split('----- BEGIN ' + delimiter + ' -----<br />\r\n\t\t')[1] \
                .split('<br />')[0]
    except Exception:
        return 'Failed to get the challenge, check your session id.'

    # Compute the result
    computed = callback(string)

    # Submit the result
    r = requests.get(url + computed, cookies=cookies)

    # Return the answer
    return r.text
