# nsanity-checker
performs a large sanity check across several tables in the netsapiens database


currently checks:
- every DT rule has a DT taBLE
- every DT table has a domain
- every domain has a reseller/territory
- every hunt group has a call queue
- every call queue has a user
- every user has a domain
- every device has a user
- every timeframe has a user
- every answering rule has a user

prints all results to terminal

### INSTALLATION:
clone repo:
```bash
git clone https://github.com/DallanL/nsanity-checker.git
```

setup venv:
```bash
cd nsanity-checker
python3 -m venv venv
```


### USAGE:

activate venv and install reqs:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

```bash
python3 nsanity.py
```

ctivate venv when done:
```bash
deactivate
```
