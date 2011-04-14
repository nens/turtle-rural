import re
import sys

if __name__ == '__main__':

    try:
        print "Try to import turtlebase..."
        import turtlebase
        
        p = re.compile(".*turtlebase-(\d{1,2})[.](\d{1,2})_r(\d{1,})-.*")
        m = p.match(turtlebase.__file__)
        print "turtlebase version: ", [int(value) for value in m.groups()]

        print "Try to import nens..."
        import nens
        
        p = re.compile(".*nens-(\d{1,2})[.](\d{1,2}).*")
        m = p.match(nens.__file__)
        print "nens version: " , [int(value) for value in m.groups()]

        exit_code = 1
    except ImportError:
        # turtlebase is not installed, which is what we want
        exit_code = 0

    sys.exit(exit_code)
