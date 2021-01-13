# Bypass-OTF_Proxy

## Version 0.2

# Overview

This repository contains 3 applications:

- An application to set up, maintain, and report on mirrors, onions, and ipfs nodes.
- An application to report on logfiles generated by [EOTK](https://github.com/alecmuffett/eotk) (the onion proxy) and Nginx. (WIP: Cloudfront log files)
- A Flask application which serves as a reporting API for the Bypass Censorship Extension, as well as a front-end for viewing:
  - Reports from that API
  - Current mirrors/onions and their status
  - EOTK log file reporting

# System

All of this has been tested on Ubuntu 18.04 LTS. It should work on any Ubuntu/Debian based system. It has not been tested on Mac OS or Windows.

# Prerequisites

You need (* are required): 

- a server to host this*
- At least one account to create CDN distributions*:
  - an AWS account that has permission to create/read/write Cloudfront Distributions
  - a Fastly account that has permission to create new configurations
  - an Azure account with permissions to create new CDN distributions
- An AWS account and permission to read/write S3 buckets
- a Github repo for mirrors in JSON format that is read by the [Bypass Censorship Extension](https://github.com/OpenTechFund/bypass-censorship-extension) browser extension. An example [is here](https://github.com/OpenTechFund/bypass-mirrors)*

If you want to add onions, the best method is using Alec Muffett's [EOTK (Enterprise Onion ToolKit)](https://github.com/alecmuffett/eotk). One way to mine vanity .onion addresses is to use [eschalot](https://github.com/ReclaimYourPrivacy/eschalot). At this time, onion addition is not automated.

# Setup 

```
git clone https://github.com/OpenTechFund/bypass-otf_proxy
cd bypass-otf_proxy
pipenv install
pipenv shell
cd bcapp
git clone git@github.com:fastly/fastly-py.git
```

You can use any other python environment manager you choose, use the requirements file instead of the Pipfile.

# Setting up the Database

In order to report on domains using this command line app, you'll need to make sure the database is set up. You can use Sqllite, Postgresql or MySql. Add the database URL in the .env file (see .env file creation docs in [Flask app documentation](bcapp/flaskapp/README.md))

Once the database is set up, and accessible, and you are in the virtual environment:

```
cd bcapp/flaskapp
flask db init
flask db migrate
flask db upgrade
```

# Mirror Application

The use case for this application is that there are websites which has been censored by some state actor that you want people to have access to. This will allow you to set up and maintain proxy "mirrors' using CDNs (Content Display Networks), as well as real mirror URLs (manually) and onion addresses (manually.)

## Usage
```
Usage: python automation.py [OPTIONS]

Options:
  --testing                       Domain testing of all available mirrors & onions
  --domain TEXT                   Domain to act on
  --proxy TEXT                    Proxy server to use for testing/domain
                                  detail.
  --existing TEXT                 Mirror exists already, just add to github.
  --replace TEXT                  Mirror/onion to replace.
  --delete                        Delete a domain from list
  --remove TEXT                   Mirror or onion to remove
  --domain_list                   List all domains and mirrors/onions
  --mirror_list                   List mirrors for domain
  --mirror_type [cloudfront|azure|fastly|onion|ipsf]
                                  Type of mirror
  --nogithub                      Do not add to github
  --report                        Get report from api database
  --mode [daemon|web|console]     Mode: daemon, web, console
  --help                          Show this message and exit.
```

## Listing

To get a list of all domains and mirrors use:
`python automation.py --domain_list`

To get a list of one domain and it's mirrors (and test each) use:
`python automation.py --domain=domain.com`

(Note: This also works with URLs. If the URL has a '&', use quotes in this request - e.g. --domain='http://www.youtube.com/watch?v=xxxxxxxxxxxx&list=WL')

## Testing:

`python automation.py --testing`

This goes through the list of all domains, testing each domain, mirror and onion (ipfs testing forthcoming), and adding to the database.

## Domain addition: 

To add an existing mirror (one that you have already set up, including onions) use:

`python automation.py --domain=domain.com --existing=domain_mirror.com`

This will add a mirror (or onion, if it is a .onion) to the json file. If the domain doesn't exist in the json file, it will add the domain.

To add a new mirror automatically for Cloudfront, Fastly, or Azure use:

`python automation.py --domain=domain.com --mirror_type=cloudfront|fastly|azure|onion|ipfs`

(The cloudfront, fastly, and azure processes are automated. The onion and ipsf processes are not yet.)

If you want a cloudfront distro, it will create that for you, and tell you the domain. For Fastly and Azure, you'll have to specify the Fastly and Azure subdomain (Cloudfront specifies a subdomain for you, Fastly and Azure require you to define it.)

All configurations are in auto.cfg (see auto.cfg-example)

## Mirror replacement

To replace one mirror with another use:

`python automation.py --domain=domain.com --replace=oldmirror.com --existing=newmirror.com`

or
*(implemented for cloudfront so far)*

`python automation.py --domain=domain.com --replace=oldmirror.com --mirror_type=cloudfront|fastly|azure|ipfs`

If the mirror_type is defined, the replacement will be automated, and whatever is needed to reset the mirror url will be done. 

## Domain Deletion

To delete an entire domain and it's mirrors/onions, use:

`python automation.py --domain=domain.com --delete`

## Mode

Daemon mode is for things like cron jobs - it suppresses output.

## Notes

There are some defaults for all four systems, and if you want to change those, you would need to go to the documentation for each and modify the code:

* [Cloudfront](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront.html#CloudFront.Client.create_distribution)
* [Fastly](https://docs.fastly.com/api/config) and [Fastly-Python](https://github.com/maxpearl/fastly-py)
* [Azure](https://docs.microsoft.com/en-us/python/api/overview/azure/cdn?view=azure-python)

Problems you might encounter:

- IP address of proxy source (Cloudfront, Fastly, etc.) blocked by origin website by policy
- Assets (css, video etc.) not completely proxied properly, leading to bad formatting or missing content
- Other proxy difficulties that are hard to diagnose (for example, some  websites proxy fine with one service but not another.)

## To Use IPFS (Plus YouTube Dowloader)

### Install IPFS

Follow [these instructions](https://docs.ipfs.io/how-to/command-line-quick-start/#install-ipfs) from IPFS.

Initialize the repository: `ipfs init --profile server`. Copy the IPFS peer identity and place it in the auto.cfg file under [SYSTEM] (You can leave out the --profile server option if you are not running this in a datacenter.)

Add ipfs as a service to your server. Create /etc/systemd/system/ipfs.service:

```
[Unit]
Description=IPFS daemon
After=network.target
[Service]
User=ubuntu
ExecStart=/usr/local/bin/ipfs daemon
[Install]
WantedBy=multiuser.target
```

Start the service:

`sudo service ipfs start`


### Install YouTube Downloader

```
sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
sudo chmod a+rx /usr/local/bin/youtube-dl
```
Make sure that `python` is correctly associated with `python3` in update-alternatives

Add the following configuration file to the home directory of the user who is running this app (such as 'ubuntu'):

```
# Lines starting with # are comments

# Always extract audio
#-x

# Do not copy the mtime
#--no-mtime

# Save all videos under /var/www/ipfs/
-o /var/www/ipfs/%(id)s.%(ext)s
```

Configuration options can be found in the [youtube-dl repository](https://github.com/ytdl-org/youtube-dl).

# Log Reporting Analysis Application

## Usage

```
Usage: python log_stats.py [OPTIONS]

Options:
  --percent INTEGER    Floor percentage to display for agents and codes
                       (default is 5%)
  --num INTEGER        Top number of pages to display (default is 10)
  --recursive          Descent through directories
  --unzip              Unzip and analyze zipped log files (bz2 files only)
  --daemon             Run in daemon mode. Suppresses all output.
  --skipsave           Skip saving log file to S3
  --justsave           Just save log files to S3, don't run any analysis.
  --read_s3            Read logfiles from S3, not from local paths.
  --help               Show this message and exit.
```

The [configuration file](bcapp/auto.cfg-example) contains two important variables under the 'LOGS' directive: 

```
[LOGS]
path_file = /path/to/logpaths.txt
log_storage_bucket = s3_bucket_to_store_logs
```

The path_file is the location of the file which contains the paths for where to find the EOT logs. The format of this file should look something like:

```
domain1.org|/path/to/eotk/projects.d/domain1.d/log.d
domain2.org|/path/to/eotk/projects.d/domain2.d/log.d
domain3.com|/path/to/eotk/projects.d/domain3.d/log.d
```

ETOK stores the files in projects.d under each project. You'll almost certainly want to use the --recursive option

Log files and analysis goes to S3 in the bucket specified in "log_storage_bucket" in the configuration file. The --skipsave option will skip saving the log files to S3 (the analysis files will still be saved.) You can run this in daemon mode, which suppresses all output. This is great for periodic cron jobs.

Certain paths will be ignored based on what's stored in the database for the domain. The code eliminates the assets from reporting and paths stored for the domain in the database.

Use the 'read_s3' options to read files from the S3 bucket, and not look at local files. 

# Flask Application (work in progress)

See documentation [here](bcapp/flaskapp/README.md)
