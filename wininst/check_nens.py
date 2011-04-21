import re
import sys

if __name__ == '__main__':

    try:
        print "Try to import nens..."
        import nens
        
        p = re.compile(".*nens-(\d{1,2})[.](\d{1,2}).*")
        m = p.match(nens.__file__)
        print "nens version: " , [int(value) for value in m.groups()]

        exit_code = 1
    except ImportError:
        print "nens apreas to be not installed" # which is what we want
        exit_code = 0

    sys.exit(exit_code)
