# mike_pizza

# a smart mpd client-server
# allows xmobar to get the song stats without having to constantly query the mpd server

from mpd import MPDClient
import threading
import time

songchanged = True 

def pad(string, length):
    return string + (" " * (length - len(string)))

def rotate(idx, string):
    newidx = 0
    string = string + " ** "
    if (idx + 1 < len(string)): 
        newidx = idx+1
    newstring = string[idx: idx+50]
    if (len(newstring) < 50):
        tail = string[0:50-(len(newstring))]
        newstring = newstring + tail 

    # final dot touches
    return (newidx, newstring) 

def rottest():
    string = "A"*20 + "B"*20 + "C" * 20 #+ "D"*20 + "E" *20 + "F" * 20
    i = 0
    while True:
        (i, pstr) =  rotate(i, string)
        print pstr
        time.sleep(.5)

def color(string, xcolor):
    return "<fc=" + xcolor + ">" + string + "</fc>"

def updateCurSong(filename, song):
    f = open(filename, "w")
    f.write(song)
    f.close()

def changeSong(newstate, lock):
    global songchanged

    lock.acquire()
    songchanged = newstate
    lock.release()
    

def songChange(lock):
    global songchanged
    
    lock.acquire() 
    state = songchanged 
    lock.release()

    return state

def getSong(client, filename, lock, cv):

    while True:

        # the player has changed
        # we will always check for a new song
        # but we will also check to see if 
        # we are paused

        client.status()
        state = client.status()["state"]
        statestr = ""

        if state == "play":
            statestr = "playing: "
        elif state == "pause":
            statestr = "paused: "
        elif state == "stop": 
            statestr = "mpd: <" + color("off", "red") + ">"
        else:
            statestr = "[!!]"

        tags = client.currentsong() 

        changeSong(False, lock)
        cv.acquire()
        cv.notify_all()

        songstr = ""
        if "artist" in tags.keys():
            songstr  = tags["artist"]
            songstr += " - "

        if "title" in tags.keys():
            songstr += tags["title"]

        cv.release() # otherwise we block clientLoop
        if (len(songstr) >= 50):
            i = 0
            while not (songChange(lock)):
                (i, sliced) = rotate(i, songstr)
                sliced = pad(sliced, 50)
                print statestr + color(sliced, "#ffffff")
                updateCurSong(filename, statestr + color(sliced, "#ffffff"))
                time.sleep(1)
        else:
            while not (songChange(lock)):
                print statestr + color(songstr, "#ffffff")
                updateCurSong(filename, statestr + color(songstr, "#ffffff"))
                #cv.wait() 
                time.sleep(3)

def clientLoop(client, lock, cv):

    while True: 
        cv.acquire()
        cv.notify_all()
        while songChange(lock):
            cv.wait()
        client.idle("player")
        changeSong(True, lock)
        

def init(host, port, songfile):

    client = MPDClient()
    client.connect(host, port)

    changelock = threading.Lock()
    cv = threading.Condition()
    songwriter = threading.Thread(target=getSong, args=[client, songfile, changelock, cv])
    songwriter.start()
    clientLoop(client, changelock, cv)

def main():
    init("localhost", 6600, "/tmp/song.txt")
 
if __name__ == "__main__":
    main()
