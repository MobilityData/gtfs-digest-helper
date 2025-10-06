# gtfs-digest-helper
- Click on Generate _year_-_month_ Digest
- See contribition stats and active PR's
- Search any word in any discussion (issues and pull requests)

## How it works
Every month, a script has to be run to get all data since 2015 until last month (script below)
Then, an API call gets the data on current month and the page compares historical and last month data.

## Load data every end of month

In terminal, run:

```
export GITHUB_TOKEN="your_githib_api_token"
python3 fetch_github.py
```

Then replace files in data/cleaned-data with last exported files
