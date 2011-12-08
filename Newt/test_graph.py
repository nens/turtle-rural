from matplotlib.pyplot import figure, show
import numpy

x1 = numpy.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
y1 = numpy.array([2.0, 1.5, 0.75, 0.75, 1.5, 2.0])
#y1 = numpy.sin(2 * numpy.pi * x1)
print y1
#y2 = 1.2 * numpy.sin(4 * numpy.pi * x1)

x2 = [1.5, 3.0]
y2 = (0 * x1) + 1.5

fig = figure()
ax1 = fig.add_subplot(111)

ax1.plot(x1, y1, x1, y2, color='black')
ax1.fill_between(x1, y1, y2, where=y2 >= y1, facecolor='blue', interpolate=True)
                 #, where=y2 >= y1, interpolate=True)
ax1.set_ylabel('between y1 and 0')

show()
