import re

def getVoteCount():
    string = '<choice id="102349" votetotal="1735"></choice>'

    p = re.compile('votetotal="(\d+)"')
    voteCount =  int(p.findall(string)[0])
    return voteCount
    # print m.group()

print getVoteCount()

