import os
import shutil
import sys


def main():
    """Copy .tbx and .ini files to buildout's bin directory.

    As the only argument, we get a buildout bin directory. We're
    supposed to be run from buildout with collective.recipe.cmd.

    Note: don't override existing .ini files!

    """
    bin_dir = sys.argv[1]
    # bin_dir_contents = os.listdir(bin_dir)
    our_dir = os.path.dirname(os.path.abspath(__file__))
    our_dir_contents = os.listdir(our_dir)
    copy_filenames = [f for f in our_dir_contents
                      if f.endswith('.tbx')
                      or f.endswith('.dll')
                      or f.endswith('.exe')
                      or f.endswith('.ini')
                      or f.endswith('.csv')
                      or f.endswith('.xsl')
                      or f.endswith('.gif')
                     ]
    # conditional_copy_filenames = [f for f in our_dir_contents
    #                               if f.endswith('.ini')]

    # Just copy all .tbx (and so) files.
    for copy_filename in copy_filenames:
        from_ = os.path.join(our_dir, copy_filename)
        to = os.path.join(bin_dir, copy_filename)
        shutil.copy(from_, to)
        print "Copied %s to %s" % (from_, to)

    # # Only copy .ini files if they don't already exist.
    # for conditional_copy_filename in conditional_copy_filenames:
    #     from_ = os.path.join(our_dir, conditional_copy_filename)
    #     to = os.path.join(bin_dir, conditional_copy_filename)
    #     if conditional_copy_filename in bin_dir_contents:
    #         print "Not copying %s as %s already exists" % (from_, to)
    #         continue
    #     shutil.copy(from_, to)
    #     print "Copied %s to %s" % (from_, to)
