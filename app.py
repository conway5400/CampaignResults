#all of my imports
from flask import Flask, request, render_template, session, redirect
import requests
from bs4 import BeautifulSoup
import re
import threading
from twilio.rest import Client
from datetime import datetime
from pytz import timezone    
import atexit
from apscheduler.scheduler import Scheduler

#cron job configurations here
cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

# twilio credientals & setup here
account_sid = "AC4a7cb7028d915e895cdcfd031e89f5da"
auth_token = "9033452bc7ab446c9624e7331f585939"
client = Client(account_sid, auth_token)

#flask configuration here
app = Flask(__name__)
app.secret_key = 'Teddy is the best'


#global variable declarations
lastCount = 1
lastUpdated = datetime.today()
resultsText = None
resultsJson = None
distributionList = ['+15043387662']

#function to update and get election results 
#updates the "results global object"
def updateElectionResults():
    global lastCount
    global resultsText
    global resultsJson

    print "RUNNING GET ELECTION STATUS"

    #make requests to serveer to get results & soupify them
    page = requests.get("https://s3.amazonaws.com/nola.com/elections/results/20171118.AllVotes_ByParish.xml")
    soup = BeautifulSoup(page.content, 'lxml')

    #format and set lastupdated time
    central = timezone('US/Central')
    lastUpdated = datetime.now(central)

    #get results for appropriate race
    districtBRace = soup.find(id="56076")
    sethResults = soup.find(id="102559")
    jayResults = soup.find(id="102558")

    #convert raw data into formatted numbers
    precintsReported = getPrecintsReported(districtBRace)
    totalPrecints = getTotalPrecints(districtBRace)
    sethVotes = getVoteCount(sethResults)
    jayVotes = getVoteCount(jayResults)

    #handle edge case of no votes
    if(sethVotes == 0 and jayVotes == 0):
        sethVotes = 1

    #calculate numbers
    totalVotes = float(sethVotes + jayVotes)

    #generate formatted results string
    resultsText = """
ELECTION UPDATE
TOTAL PRECINTS: {} of {} reporting
Seth:      {} // {}%
Jay:       {} // {}%
TOTAL VOTES: {}
""".format(precintsReported, totalPrecints, sethVotes, round(float(sethVotes) / totalVotes * 100, 1), jayVotes, round(float(jayVotes) / totalVotes * 100, 1), totalVotes)
    
    print ("TOTAL VOTES {} // LAST COUNT {}".format(totalVotes, lastCount))

    #check to see if these results are different than last
    if totalVotes != lastCount:
        print "Looks like last count is different from total count..."
        print resultsText
        sendTextMessageUpates()
        
    resultsJson = {
        'sethVotes' : sethVotes,
        'jayVotes' : jayVotes,
        'precintsReported' : precintsReported,
        'totalPrecints' : totalPrecints,
        'lastUpdated' : lastUpdated.strftime("%-I:%M:%S %p CST")
    }

    lastCount = int(totalVotes)
    print "Updating last count!"

#send text messages
def sendTextMessageUpates():
    print "Sending text message updates to list..."
    global resultsText
    global distributionList

    for person in distributionList:
        print "Sending text message to " + person + "...."
        client.messages.create(
        to=person,
        from_="+15042296824",
        body= resultsText)

#get vote count for a given race
def getVoteCount(input):
    input = str(input)
    p = re.compile('votetotal="(\d+)"')
    voteCount =  int(p.findall(input)[0])
    return voteCount

#get precint reporting count for a given race
def getPrecintsReported(input):
    input = str(input)
    p = re.compile('numprecinctsreporting="(\d+)"')
    precintCount =  int(p.findall(input)[0])
    return precintCount

#get total precints reporting count for a given race
def getTotalPrecints(input):
    input = str(input)
    p = re.compile('numprecinctsexpected="(\d+)"')
    precintCount =  int(p.findall(input)[0])
    return precintCount

#handle routing/view
@app.route('/')
def indexRoute():
    content = resultsJson
    return render_template('index.html', content = content)

@app.route('/subscribers')
def subscriberIndex():
    global distributionList
    content = { 'subscribers' : distributionList }
    return render_template('subscribers.html', content = content)

@app.route('/subscribers/delete/<phoneNumber>')
def deleteSubscriber(phoneNumber):
    global distributionList

    for person in distributionList:
        if person == phoneNumber:
            distributionList.remove(person)

    return redirect('/subscribers')

@app.route('/newSubscriber', methods=['POST'])
def newSubscriberRoute():
    global distributionList
    newPhone = request.form['phoneNumber']

    print("New subscriber, checking to see if this person to the list... {}".format(newPhone))

    for person in distributionList:
        if person == newPhone:
            print("This person is already on the list...")
            return redirect('/')

    print("Not on list, adding them!")
    distributionList.append(newPhone)

    return redirect('/')

@cron.interval_schedule(minutes=1)
def electionCronJob():
    print "Updating election results..."
    updateElectionResults()

# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: cron.shutdown(wait=False))

electionCronJob()

app.run()

