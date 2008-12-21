#!/usr/bin/python

####
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Created by Lincoln Quirk in 2008
# Based off of Jason Ureta's Warcraft III AutoRefresh (GPL)
####

####
# USAGE:
#  1. Start hosting a Battle.net game in Warcraft 3
#  2. Execute ./ar.py
#  3. Relax while your game fills up!
# 
# When you start the game, this program will exit automatically.
####


REFRESH_SLOTS = 12
GAME_ADDR = ('localhost', 6112)
RF_NAME = '|rAutoRefresh'           # |r means 'make this bright white'

import socket
import array
import time

def mkPacket(name, gameId):
    '''Returns the 'AutoRefresh joined...' packet as an array of unsigned bytes
    name: the username who appears to join, including any wc3 color codes
    gameId: the id of the game we are joining. (hostCounter)'''
    
    # Apparently, we get no more than 15 characters, including any color codes
    fullName = str(name)[0:15]
    
    packet = array.array('B', [
        0xF7, 0x1E, 0xff, 0x00, gameId, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xE4, 0x17, 0x00, 0x00, 0x00, 0x00
        ])
    packet.fromstring(fullName)
    packet.fromlist([
        0x00, 0x01, 0x00, 0x02, 0x00, 0x17, 0xE0, 0x7F, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])

    # overwrite that 0xff in the 3rd slot with the actual packet length
    packet[2] = len(packet)
    return packet


def startRefresh():
    '''Starts refreshing the game every 10 seconds.
    Returns True when the host starts the game.
    Raises a socket exception if we can't find any wc3 at the correct address or it times out. '''

    # Tricky flow control in this method; I use exceptions to manage it.
    class GameFull(Exception): pass
    class AlreadyStarted(Exception): pass
    class NoSuchGame(Exception): pass

    # We start at 0, guessing gameIds one by one, until we get the correct one.
    gameId = 0

    try:
        # This loop runs forever, refreshing all slots, until we see AlreadyStarted.
        while True:
            slots = []
            try:
                try:
                    # Refresh each slot. The 'slots' array holds the open sockets.
                    for i in range(0, REFRESH_SLOTS):
                        print i
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.connect(GAME_ADDR)
                        slots.append(sock)

                        # Construct and send packet.
                        wfile = sock.makefile('wb', 0)
                        wfile.write(mkPacket(RF_NAME, gameId).tostring())


                        rfile = sock.makefile('rb', -1)
                        # We never need more than a few bytes from the response,
                        # so just read 8 and convert it to a byte array.
                        responsePacket = array.array('B')
                        responsePacket.fromstring(rfile.read(8))     
                        
                        if responsePacket[1] == 5 and responsePacket[2] == 8:
                            # These are all "you failed to join because..."
                            if responsePacket[4] == 9:
                                print "full"
                                raise GameFull()
                            elif responsePacket[4] == 10:
                                print "already started"
                                raise AlreadyStarted()
                            elif responsePacket[4] == 7:
                                print "wrong gameId"
                                raise NoSuchGame()
                            else:
                                print "Failed to join - reason %d unknown" % responsePacket[4]
                        elif responsePacket[1] == 4:
                            # I think we succeeded at joining! (Let's hope; I have no idea what '4' actually means)
                            print "ok"
                        else:
                            print "Unknown response: %s" % str(responsePacket)
                            
                            
                except GameFull:
                    # When the game's full just wait 10 seconds and refresh again
                    pass

                except NoSuchGame:
                    # We guessed the wrong gameId, so try the next one.
                    gameId = (gameId + 1) % 256
                    # Don't wait the 10 seconds in this case - go ahead immediately
                    continue

            finally:
                # Always close your connections, dear! (That's what your mom said)
                # (Probably strictly not necessary, since 'slots' will be reset to [] 
                # at the beginning of the next refresh run)
                for (i, sock) in enumerate(slots):
                    print 'close %d' % i
                    sock.close()

            # Whew... take a short nap.
            time.sleep(10)

    except AlreadyStarted:  # This is the outermost Try
        return True

if __name__ == '__main__':
    startRefresh()
