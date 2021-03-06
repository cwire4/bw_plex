import os
import logging
import subprocess
import tempfile

from profilehooks import timecall

from audfprint.audfprint_match import Matcher
from audfprint.audfprint_analyze import Analyzer

LOG = logging.getLogger(__file__)


def to_time(sec):
    m, s = divmod(sec, 60)
    return '%02d:%02d' % (m, s)


def analyzer():

    a = Analyzer()
    a.n_fft = 512
    a.n_hop = a.n_fft / 2
    a.shifts = 4
    a.fail_on_error = False
    a.density = 20
    return a


def matcher():
    m = Matcher()
    m.find_time_range = True
    m.search_depth = 200
    m.verbose = True
    return m


@timecall(immediate=True)
def get_offset_end(vid, hashtable):
    an = analyzer()
    match = matcher()

    start_time = -1
    end_time = -1

    t_hop = an.n_hop / float(an.target_sr)
    rslts, dur, nhash = match.match_file(an, hashtable, vid, 1) # The number does not matter...

    for (tophitid, nhashaligned, aligntime,
         nhashraw, rank, min_time, max_time) in rslts:
            #print(tophitid, nhashaligned, aligntime, nhashraw, rank, min_time, max_time)
            end_time = max_time * t_hop
            start_time = min_time * t_hop
            LOG.debug('Started at %s (%s) in ended at %s (%s)' % (start_time, to_time(start_time),
                                                                  end_time, to_time(end_time)))
            return start_time, end_time

    LOG.debug('no result just returning -1')

    return start_time, end_time


def partial_dl(part, fn, stop=6, chunk=8000):
    # this should check the parts location first imo.
    # so we read directly from file.
    stop = part.size // stop
    p = os.path.join(os.getcwd(), '%s.mkv' % fn)

    try:
        N = 0
        with open(part.location, 'r') as ip:
            with open(p, 'wb') as outp:
                while True:
                    data = ip.read(chunk)
                    N += chunk
                    if stop and N > stop:
                        break
                    else:
                        outp.write(data)

        return p
    except Exception as e:
        #logging.exception(e)
        print('local copy failed.')

    print('copy via plex')
    session = part._session

    url = part._server.url('%s?download=1' % part.key)

    r = session.get(url, stream=True)

    with open(p, 'wb') as handle:
        sofa = 0
        for it in r.iter_content(chunk):
            print(sofa)
            if stop and sofa > stop:
                break
            handle.write(it)
            sofa += chunk

    return p


def in_dir(root, ratingkey):
    for f in os.listdir(root):
        if ratingkey in f:
            fp = os.path.join(root, f)
            return fp


@timecall(immediate=True)
def convert_and_trim(afile, fs=8000, trim=None):
    tmp = tempfile.NamedTemporaryFile(
        mode='r+b', prefix='offset_', suffix='.wav')
    tmp_name = tmp.name
    tmp.close()
    if trim is None:
        cmd = [
            'ffmpeg', '-loglevel', 'panic', '-i', afile, '-ac', '1', '-ar',
            str(fs), '-acodec', 'pcm_s16le', tmp_name
        ]
    else:
        cmd = [
            'ffmpeg', '-loglevel', 'panic', '-i', afile, '-ac', '1', '-ar',
            str(fs), '-ss', '0', '-t', str(trim), '-acodec', 'pcm_s16le',
            tmp_name
        ]

    LOG.debug('calling ffmepg with %s' % ' '.join(cmd))

    psox = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    o, e = psox.communicate()
    if not psox.returncode == 0:
        print(e)
        raise Exception("FFMpeg failed")

    return tmp_name


#@timecall(immediate=True)
def convert_and_trim_to_mp3(afile, fs=8000, trim=None, outfile=None):
    if outfile is None:
        tmp = tempfile.NamedTemporaryFile(mode='r+b', prefix='offset_', suffix='.mp3')
        tmp_name = tmp.name
        tmp.close()
        outfile = tmp_name

    cmd = ['ffmpeg', '-i', afile, '-ss', '0', '-t', str(trim), '-codec:a', 'libmp3lame', '-qscale:a', '6', outfile]

    print('calling ffmepg with %s' % ' '.join(cmd))

    psox = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    o,e = psox.communicate()
    if not psox.returncode == 0:
        print(e)
        raise Exception("FFMpeg failed")

    return outfile


if __name__ == '__main__':
    def zomg():
        print('zomg')
        ht = '' # path to db
        fp = '' # path to wav.
        from audfprint.hash_table import HashTable
        HT = HashTable(ht)
        n = get_offset_end(fp, HT)
        print(n)

    zomg()
