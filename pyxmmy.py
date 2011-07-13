# 
# Pyxmmy module: core functions for getting song and playlist info from xmms
#

import xmmsclient
import sys
import os

class Song(object):
    def __init__(self, artist = None, album = None, title = None,
                    cover = None, url = None, id = None):
        self.artist = artist
        self.album = album
        self.title = title
        self.cover = cover
        self.url = url


class Pyxmmy(object):
    def __init__(self, name):
        self.xmms = xmmsclient.XMMS(name)
        self.xmms.connect(os.getenv('XMMS_PATH'))


    def playlist(self):
        '''Returns the current playlist.'''
        ids = self.xmms.playlist_list_entries()
        ids.wait()
        return [self.song(n) for n in ids.value()]

    def playlistPos(self):
        '''Returns current playback index.'''
        pos = self.xmms.playlist_current_pos()
        pos.wait()
        return pos.value

    def currentSong(self):
        playback_id = self.xmms.playback_current_id()
        playback_id.wait()
        return self.song(playback_id.value())

    def song(self, id):
        '''Returns song corresponding to an ID value.'''
        result = self.xmms.medialib_get_info(id)
        result.wait()

        minfo = {} if result.iserror() else result.value()

        def prop(pdict, key):
            return pdict[key] if key in pdict else None

        s = Song()

        # Fill out basic song info first
        s.artist = prop(minfo, 'artist') or 'Unknown artist'
        s.title  = prop(minfo, 'title') or 'Unknown title'
        s.album  = prop(minfo, 'album') or 'Unknown album'
        s.url    = prop(minfo, 'url')
        s.id     = id

        # Get cover art, if any
        cover_hash = prop(minfo, 'picture_front')
        try:
            s.cover = self.art(cover_hash) or \
                      find_local_art(s) or \
                      get_default_art()
        except:
            s.cover = None

        return s

    def art(self, hash):
        '''Gets binary cover image data for given cover hash.'''
        if not hash:
            return None
        bindata = self.xmms.bindata_retrieve(hash)
        bindata.wait()
        return bindata.value()


def get_default_art():
    '''Returns the default cover art as binary data'''
    with open(sys.path[0] + '/default.png') as file:
        return file.read()

def find_local_art(song):
    '''Attempts to find local cover art for the given song.

       This is done by looking in the folder containing the song for any image
       file whose name resembles the song's album name. Returns None if no good
       candidate is found, or if the song is not local (and therefore we can't
       do a directory listing to look for art files).'''

    from difflib import get_close_matches
    from urlparse import urlparse
    from urllib import unquote_plus
    import re

    url = urlparse(song.url)

    # this only works for local files
    if url.scheme != 'file':
        return None

    # Get a list of image files in the song's directory
    basedir     = os.path.dirname(unquote_plus(url.path))
    image_exts  = ['png', 'jpg', 'gif', 'bmp', 'svg']
    imagefiles  = filter(re.compile('|'.join([ext + '$' for ext in image_exts]),
                    re.IGNORECASE).search, os.listdir(basedir))

    # Look for any that are close to the album title
    candidates = get_close_matches(song.album, imagefiles, cutoff = 0.6)

    # Secondarily, look for any images called 'folder', 'album', or 'cover'
    candidates += filter(re.compile('folder|album|cover',
                re.IGNORECASE).search, imagefiles)

    if len(candidates) == 0:
        return None

    with open('{0}/{1}'.format(basedir, candidates[0])) as file:
        return file.read()


