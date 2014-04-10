import nens.geom

ls = [(138585.10418, 483434.4867), (138577.64577, 483435.45535)]
pc = [(138581.464, 483435.38), (138581.616, 483436.482), (138581.688, 483433.68), (138581.734, 483437.3031), (138581.953, 483434.675)] 

sorted = nens.geom.sort_perpendicular_to_segment(ls, pc)

print sorted

abscissas = zip(nens.geom.abscissa_from_midsegment(sorted), sorted)
print "abscissas %s" % abscissas