import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from matplotlib import cm

class event():
	'''
	This class provides a way to store, read, write and visualize spike event.

	Members:
		* ``x`` (numpy ``int`` array): `x` index of spike event.
		* ``y`` (numpy ``int`` array): `y` index of spike event (not used if the spatial dimension is 1).
		* ``p`` (numpy ``int`` array): `polarity` or `channel` index of spike event.
		* ``t`` (numpy ``double`` array): `timestamp` of spike event. Time is assumend to be in ms.

	Usage:

	>>> TD = spikeFileIO.event(xEvent, yEvent, pEvent, tEvent)
	'''
	def __init__(self, xEvent, yEvent, pEvent, tEvent):
		if yEvent is None:
			self.dim = 1
		else:
			self.dim = 2

		self.x = xEvent if type(xEvent) is np.array else np.asarray(xEvent) # x spatial dimension
		self.y = yEvent if type(yEvent) is np.array else np.asarray(yEvent) # y spatial dimension
		self.p = pEvent if type(pEvent) is np.array else np.asarray(pEvent) # spike polarity
		self.t = tEvent if type(tEvent) is np.array else np.asarray(tEvent) # time stamp in ms

		self.p -= self.p.min()

	def toSpikeArray(self, samplingTime=1, dim=None):	# Sampling time in ms
		'''
		Returns a numpy tensor that contains the spike events sampled in bins of `samplingTime`.
		The array is of dimension (channels, height, time) or``CHT`` for 1D data.
		The array is of dimension (channels, height, width, time) or``CHWT`` for 2D data.

		Arguments:
			* ``samplingTime``: the width of time bin to use.
			* ``dim``: the dimension of the desired tensor. Assignes dimension itself if not provided.

		Usage:

		>>> spike = TD.toSpikeArray()
		'''
		if self.dim == 1:
			if dim is None: dim = ( np.round(max(self.p)+1).astype(int),
									np.round(max(self.x)+1).astype(int), 
									np.round(max(self.t)/samplingTime+1).astype(int) )
			frame = np.zeros((dim[0], 1, dim[1], dim[2]))
		elif self.dim == 2:
			if dim is None: dim = ( np.round(max(self.p)+1).astype(int), 
									np.round(max(self.y)+1).astype(int), 
									np.round(max(self.x)+1).astype(int), 
									np.round(max(self.t)/samplingTime+1).astype(int) )
			frame = np.zeros((dim[0], dim[1], dim[2], dim[3]))
		return self.toSpikeTensor(frame, samplingTime).reshape(dim)

	def toSpikeTensor(self, emptyTensor, samplingTime=1):	# Sampling time in ms
		'''
		Returns a numpy tensor that contains the spike events sampled in bins of `samplingTime`.
		The tensor is of dimension (channels, height, width, time) or``CHWT``.

		Arguments:
			* ``emptyTensor`` (``numpy or torch tensor``): an empty tensor to hold spike data 
			* ``samplingTime``: the width of time bin to use.

		Usage:

		>>> spike = TD.toSpikeTensor( torch.zeros((2, 240, 180, 5000)) )
		'''
		if self.dim == 1:
			xEvent = np.round(self.x).astype(int)
			pEvent = np.round(self.p).astype(int)
			tEvent = np.round(self.t/samplingTime).astype(int)
			validInd = np.argwhere((xEvent < emptyTensor.shape[2]) &
								   (pEvent < emptyTensor.shape[0]) &
								   (tEvent < emptyTensor.shape[3]))
			emptyTensor[pEvent[validInd],
						0, 
				  		xEvent[validInd],
				  		tEvent[validInd]] = 1/samplingTime
		elif self.dim == 2:
			xEvent = np.round(self.x).astype(int)
			yEvent = np.round(self.y).astype(int)
			pEvent = np.round(self.p).astype(int)
			tEvent = np.round(self.t/samplingTime).astype(int)
			validInd = np.argwhere((xEvent < emptyTensor.shape[2]) &
								   (yEvent < emptyTensor.shape[1]) & 
								   (pEvent < emptyTensor.shape[0]) &
								   (tEvent < emptyTensor.shape[3]))
			emptyTensor[pEvent[validInd], 
				  		yEvent[validInd],
				  		xEvent[validInd],
				  		tEvent[validInd]] = 1/samplingTime
		return emptyTensor

def spikeArrayToEvent(spikeMat, samplingTime=1):
	'''
	Returns TD event from a numpy array (of dimension 3 or 4).
	The numpy array must be of dimension (channels, height, time) or``CHT`` for 1D data.
	The numpy array must be of dimension (channels, height, width, time) or``CHWT`` for 2D data.

	Arguments:
		* ``spikeMat``: numpy array with spike information.
		* ``samplingTime``: time width of each time bin.

	Usage:

	>>> TD = spikeFileIO.spikeArrayToEvent(spike)
	'''
	if spikeMat.ndim == 3:
		spikeEvent = np.argwhere(spikeMat > 0)
		xEvent = spikeEvent[:,1]
		yEvent = None
		pEvent = spikeEvent[:,0]
		tEvent = spikeEvent[:,2]
	elif spikeMat.ndim == 4:
		spikeEvent = np.argwhere(spikeMat > 0)
		xEvent = spikeEvent[:,2]
		yEvent = spikeEvent[:,1]
		pEvent = spikeEvent[:,0]
		tEvent = spikeEvent[:,3]
	else:
		raise Exception('Expected numpy array of 3 or 4 dimension. It was {}'.format(spikeMat.ndim))

	return event(xEvent, yEvent, pEvent, tEvent * samplingTime) 

def read1Dspikes(filename):
	'''
	Reads one dimensional binary spike file and returns a TD event.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 40 bit number.
		* First 16 bits (bits 39-24) represent the neuronID.
		* Bit 23 represents the sign of spike event: 0=>OFF event, 1=>ON event.
		* the last 23 bits (bits 22-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.

	Usage:

	>>> TD = spikeFileIO.read1Dspikes(file_path)
	'''
	with open(filename, 'rb') as inputFile:
		inputByteArray = inputFile.read()
	inputAsInt = np.asarray([x for x in inputByteArray])
	xEvent =  (inputAsInt[0::5] << 8)  |  inputAsInt[1::5]
	pEvent =   inputAsInt[2::5] >> 7
	tEvent =( (inputAsInt[2::5] << 16) | (inputAsInt[3::5] << 8) | (inputAsInt[4::5]) ) & 0x7FFFFF
	return event(xEvent, None, pEvent, tEvent/1000)	# convert spike times to ms

def encode1Dspikes(filename, TD):
	'''
	Writes one dimensional binary spike file from a TD event.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 40 bit number.
		* First 16 bits (bits 39-24) represent the neuronID.
		* Bit 23 represents the sign of spike event: 0=>OFF event, 1=>ON event.
		* the last 23 bits (bits 22-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.
		* ``TD`` (an ``spikeFileIO.event``): TD event.

	Usage:

	>>> spikeFileIO.write1Dspikes(file_path, TD)
	'''
	if TD.dim != 1: 	raise Exception('Expected Td dimension to be 1. It was: {}'.format(TD.dim))
	xEvent = np.round(TD.x).astype(int)
	pEvent = np.round(TD.p).astype(int)
	tEvent = np.round(TD.t * 1000).astype(int)	# encode spike time in us
	outputByteArray = bytearray(len(tEvent) * 5)
	outputByteArray[0::5] = np.uint8( (xEvent >> 8) & 0xFF00 ).tobytes()
	outputByteArray[1::5] = np.uint8( (xEvent & 0xFF) ).tobytes()
	outputByteArray[2::5] = np.uint8(((tEvent >> 16) & 0x7F) | (pEvent.astype(int) << 7) ).tobytes()
	outputByteArray[3::5] = np.uint8( (tEvent >> 8 ) & 0xFF ).tobytes()
	outputByteArray[4::5] = np.uint8(  tEvent & 0xFF ).tobytes()
	with open(filename, 'wb') as outputFile:
		outputFile.write(outputByteArray)

def read2Dspikes(filename):
	'''
	Reads two dimensional binary spike file and returns a TD event.
	It is the same format used in neuromorphic datasets NMNIST & NCALTECH101.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 40 bit number.
		* First 8 bits (bits 39-32) represent the xID of the neuron.
		* Next 8 bits (bits 31-24) represent the yID of the neuron.
		* Bit 23 represents the sign of spike event: 0=>OFF event, 1=>ON event.
		* The last 23 bits (bits 22-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.

	Usage:

	>>> TD = spikeFileIO.read2Dspikes(file_path)
	'''
	with open(filename, 'rb') as inputFile:
		inputByteArray = inputFile.read()
	inputAsInt = np.asarray([x for x in inputByteArray])
	xEvent =   inputAsInt[0::5]
	yEvent =   inputAsInt[1::5]
	pEvent =   inputAsInt[2::5] >> 7
	tEvent =( (inputAsInt[2::5] << 16) | (inputAsInt[3::5] << 8) | (inputAsInt[4::5]) ) & 0x7FFFFF
	return event(xEvent, yEvent, pEvent, tEvent/1000)	# convert spike times to ms

def encode2Dspikes(filename, TD):
	'''
	Writes two dimensional binary spike file from a TD event.
	It is the same format used in neuromorphic datasets NMNIST & NCALTECH101.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 40 bit number.
		* First 8 bits (bits 39-32) represent the xID of the neuron.
		* Next 8 bits (bits 31-24) represent the yID of the neuron.
		* Bit 23 represents the sign of spike event: 0=>OFF event, 1=>ON event.
		* The last 23 bits (bits 22-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.
		* ``TD`` (an ``spikeFileIO.event``): TD event.

	Usage:

	>>> spikeFileIO.write2Dspikes(file_path, TD)
	'''
	if TD.dim != 2: 	raise Exception('Expected Td dimension to be 2. It was: {}'.format(TD.dim))
	xEvent = np.round(TD.x).astype(int)
	yEvent = np.round(TD.y).astype(int)
	pEvent = np.round(TD.p).astype(int)
	tEvent = np.round(TD.t * 1000).astype(int)	# encode spike time in us
	outputByteArray = bytearray(len(tEvent) * 5)
	outputByteArray[0::5] = np.uint8(xEvent).tobytes()
	outputByteArray[1::5] = np.uint8(yEvent).tobytes()
	outputByteArray[2::5] = np.uint8(((tEvent >> 16) & 0x7F) | (pEvent.astype(int) << 7) ).tobytes()
	outputByteArray[3::5] = np.uint8( (tEvent >> 8 ) & 0xFF ).tobytes()
	outputByteArray[4::5] = np.uint8(  tEvent & 0xFF ).tobytes()
	with open(filename, 'wb') as outputFile:
		outputFile.write(outputByteArray)

def read3Dspikes(filename):
	'''
	Reads binary spike file for spike event in height, width and channel dimension and returns a TD event.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 56 bit number.
		* First 12 bits (bits 56-44) represent the xID of the neuron.
		* Next 12 bits (bits 43-32) represent the yID of the neuron.
		* Next 8 bits (bits 31-24) represents the channel ID of the neuron.
		* The last 24 bits (bits 23-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.

	Usage:

	>>> TD = spikeFileIO.read3Dspikes(file_path)
	'''
	with open(filename, 'rb') as inputFile:
		inputByteArray = inputFile.read()
	inputAsInt = np.asarray([x for x in inputByteArray])
	xEvent =  (inputAsInt[0::7] << 4 ) | (inputAsInt[1::7] >> 4 )
	yEvent =  (inputAsInt[2::7] )    | ( (inputAsInt[1::7] & 0x0F) << 8 )
	pEvent =   inputAsInt[3::7]
	tEvent =( (inputAsInt[4::7] << 16) | (inputAsInt[5::7] << 8) | (inputAsInt[6::7]) )
	return event(xEvent, yEvent, pEvent, tEvent/1000)	# convert spike times to ms

def encode3Dspikes(filename, TD):
	'''
	Writes binary spike file for TD event in height, width and channel dimension.
	
	The binary file is encoded as follows:
		* Each spike event is represented by a 56 bit number.
		* First 12 bits (bits 56-44) represent the xID of the neuron.
		* Next 12 bits (bits 43-32) represent the yID of the neuron.
		* Next 8 bits (bits 31-24) represents the channel ID of the neuron.
		* The last 24 bits (bits 23-0) represent the spike event timestamp in microseconds.

	Arguments:
		* ``filename`` (``string``): path to the binary file.
		* ``TD`` (an ``spikeFileIO.event``): TD event.

	Usage:

	>>> spikeFileIO.write3Dspikes(file_path, TD)
	'''
	if TD.dim != 2: 	raise Exception('Expected Td dimension to be 2. It was: {}'.format(TD.dim))
	xEvent = np.round(TD.x).astype(int)
	yEvent = np.round(TD.y).astype(int)
	pEvent = np.round(TD.p).astype(int)
	tEvent = np.round(TD.t * 1000).astype(int)	# encode spike time in us
	outputByteArray = bytearray(len(tEvent) * 7)
	outputByteArray[0::7] = np.uint8(xEvent >> 4).tobytes()
	outputByteArray[1::7] = np.uint8( ((xEvent << 4) & 0xFF) | (yEvent >> 8) & 0xFF00 ).tobytes()
	outputByteArray[2::7] = np.uint8(	yEvent & 0xFF ).tobytes()
	outputByteArray[3::7] = np.uint8(   pEvent ).tobytes()
	outputByteArray[4::7] = np.uint8(  (tEvent >> 16 ) & 0xFF ).tobytes()
	outputByteArray[5::7] = np.uint8(  (tEvent >> 8 ) & 0xFF ).tobytes()
	outputByteArray[6::7] = np.uint8(   tEvent & 0xFF ).tobytes()
	with open(filename, 'wb') as outputFile:
		outputFile.write(outputByteArray)

def read1DnumSpikes(filename):
	'''
	Reads a tuple specifying neuron, start of spike region, end of spike region and number of spikes from binary spike file.
	
	The binary file is encoded as follows:
		* Number of spikes data is represented by an 80 bit number.
		* First 16 bits (bits 79-64) represent the neuronID.
		* Next 24 bits (bits 63-40) represents the start time in microseconds.
		* Next 24 bits (bits 39-16) represents the end time in microseconds.
		* Last 16 bits (bits 15-0) represents the number of spikes.
	
	Arguments:
		* ``filename`` (``string``): path to the binary file

	Usage:

	>>> nID, tSt, tEn, nSp = spikeFileIO.read1DnumSpikes(file_path)
	``tSt`` and ``tEn`` are returned in milliseconds
	'''
	with open(filename, 'rb') as inputFile:
		inputByteArray = inputFile.read()
	inputAsInt = np.asarray([x for x in inputByteArray])
	neuronID =  (inputAsInt[0::10] << 8)  |  inputAsInt[1::10]
	tStart   =  (inputAsInt[2::10] << 16) | (inputAsInt[3::10] << 8) | (inputAsInt[4::10])
	tEnd     =  (inputAsInt[5::10] << 16) | (inputAsInt[6::10] << 8) | (inputAsInt[7::10])
	nSpikes  =  (inputAsInt[8::10] << 8)  |  inputAsInt[9::10]
	return neuronID, tStart/1000, tEnd/1000, nSpikes	# convert spike times to ms

def encode1DnumSpikes(filename, nID, tSt, tEn, nSp):
	'''
	Writes binary spike file given a tuple specifying neuron, start of spike region, end of spike region and number of spikes.
	
	The binary file is encoded as follows:
		* Number of spikes data is represented by an 80 bit number
		* First 16 bits (bits 79-64) represent the neuronID
		* Next 24 bits (bits 63-40) represents the start time in microseconds
		* Next 24 bits (bits 39-16) represents the end time in microseconds
		* Last 16 bits (bits 15-0) represents the number of spikes
	
	Arguments:
		* ``filename`` (``string``): path to the binary file
		* ``nID`` (``numpy array``): neuron ID
		* ``tSt`` (``numpy array``): region start time (in milliseconds)
		* ``tEn`` (``numpy array``): region end time (in milliseconds)
		* ``nSp`` (``numpy array``): number of spikes in the region

	Usage:

	>>> spikeFileIO.encode1DnumSpikes(file_path, nID, tSt, tEn, nSp)
	'''
	neuronID = np.round(nID).astype(int)
	tStart   = np.round(tSt * 1000).astype(int)	# encode spike time in us
	tEnd     = np.round(tEn * 1000).astype(int)	# encode spike time in us
	nSpikes  = np.round(nSp).astype(int)
	outputByteArray = bytearray(len(neuronID) * 10)
	outputByteArray[0::10] = np.uint8( neuronID >> 8  ).tobytes()
	outputByteArray[1::10] = np.uint8( neuronID       ).tobytes()
	outputByteArray[2::10] = np.uint8( tStart   >> 16 ).tobytes()
	outputByteArray[3::10] = np.uint8( tStart   >> 8  ).tobytes()
	outputByteArray[4::10] = np.uint8( tStart         ).tobytes()
	outputByteArray[5::10] = np.uint8( tEnd     >> 16 ).tobytes()
	outputByteArray[6::10] = np.uint8( tEnd     >> 8  ).tobytes()
	outputByteArray[7::10] = np.uint8( tEnd           ).tobytes()
	outputByteArray[8::10] = np.uint8( nSpikes  >> 8  ).tobytes()
	outputByteArray[9::10] = np.uint8( nSpikes        ).tobytes()
	with open(filename, 'wb') as outputFile:
		outputFile.write(outputByteArray)

def _showTD1D(TD, frameRate=24, preComputeFrames=True, repeat=False):
	if TD.dim !=1:	raise Exception('Expected Td dimension to be 1. It was: {}'.format(TD.dim))
	fig = plt.figure()
	interval = 1e3 / frameRate					# in ms
	xDim = TD.x.max()+1
	tMax = TD.t.max()
	tMin = TD.t.min()
	pMax = TD.p.max()+1
	minFrame = int(np.floor(tMin / interval))
	maxFrame = int(np.ceil(tMax / interval )) + 1

	# ignore preComputeFrames

	def animate(i):
		fig.clear()
		tEnd = (i + minFrame + 1) * interval
		ind  = (TD.t < tEnd)
		# plot raster
		plt.plot(TD.t[ind], TD.x[ind], '.')
		# plt.plot(TD.t[ind], TD.x[ind], '.', c=cm.hot(TD.p[ind]))
		# plot raster scan line
		plt.plot([tEnd + interval, tEnd + interval], [0, xDim])
		plt.axis((tMin -0.1*tMax, 1.1*tMax, -0.1*xDim, 1.1*xDim))
		plt.draw()


	anim = animation.FuncAnimation(fig, animate, frames=maxFrame, interval=42, repeat=repeat) # 42 means playback at 23.809 fps

	plt.show()

def _showTD2D(TD, frameRate=24, preComputeFrames=True, repeat=False):
	if TD.dim != 2: 	raise Exception('Expected Td dimension to be 2. It was: {}'.format(TD.dim))
	fig = plt.figure()
	interval = 1e3 / frameRate					# in ms
	xDim = TD.x.max()+1
	yDim = TD.y.max()+1
	
	if preComputeFrames is True:
		minFrame = int(np.floor(TD.t.min() / interval))
		maxFrame = int(np.ceil(TD.t.max() / interval ))
		image    = plt.imshow(np.zeros((yDim, xDim, 3)))
		frames   = np.zeros( (maxFrame-minFrame, yDim, xDim, 3))

		# precompute frames
		for i in range(len(frames)):
			tStart = (i + minFrame) * interval
			tEnd = (i + minFrame + 1) * interval
			timeMask = (TD.t >= tStart) & (TD.t < tEnd)
			rInd = (timeMask & (TD.p == 1))
			gInd = (timeMask & (TD.p == 2))
			bInd = (timeMask & (TD.p == 0))
			frames[i, TD.y[rInd], TD.x[rInd], 0] = 1
			frames[i, TD.y[gInd], TD.x[gInd], 1] = 1
			frames[i, TD.y[bInd], TD.x[bInd], 2] = 1

		def animate(frame):
			image.set_data(frame)
			return image

		anim = animation.FuncAnimation(fig, animate, frames=frames, interval=42, repeat=repeat)

	else:
		minFrame = int(np.floor(TD.t.min() / interval))
		def animate(i):
			tStart = (i + minFrame) * interval
			tEnd = (i + minFrame + 1) * interval
			frame  = np.zeros((yDim, xDim, 3))
			timeMask = (TD.t >= tStart) & (TD.t < tEnd)
			rInd = (timeMask & (TD.p == 1))
			gInd = (timeMask & (TD.p == 2))
			bInd = (timeMask & (TD.p == 0))
			frame[TD.y[rInd], TD.x[rInd], 0] = 1
			frame[TD.y[gInd], TD.x[gInd], 1] = 1
			frame[TD.y[bInd], TD.x[bInd], 2] = 1
			plot = plt.imshow(frame)
			return plot

		anim = animation.FuncAnimation(fig, animate, interval=42, repeat=repeat) # 42 means playback at 23.809 fps

	# # save the animation as an mp4.  This requires ffmpeg or mencoder to be
	# # installed.  The extra_args ensure that the x264 codec is used, so that
	# # the video can be embedded in html5.  You may need to adjust this for
	# # your system: for more information, see
	# # http://matplotlib.sourceforge.net/api/animation_api.html
	# if saveAnimation: anim.save('showTD_animation.mp4', fps=30)

	plt.show()

def showTD(TD, frameRate=24, preComputeFrames=True, repeat=False):
	'''
	Visualizes TD event.

	Arguments:
		* ``TD``: spike event to visualize.
		* ``frameRate``: framerate of visualization.
		* ``preComputeFrames``: flag to enable precomputation of frames for faster visualization. Default is ``True``.
		* ``repeat``: flag to enable repeat of animation. Default is ``False``.

	Usage:

	>>> showTD(TD)
	'''
	if TD.dim == 1:
		_showTD1D(TD, frameRate=frameRate, preComputeFrames=preComputeFrames, repeat=repeat)		
	else:
		_showTD2D(TD, frameRate=frameRate, preComputeFrames=preComputeFrames, repeat=repeat)


# def spikeMat2TD(spikeMat, samplingTime=1):		# Sampling time in ms
# 	addressEvent = np.argwhere(spikeMat > 0)
# 	# print(addressEvent.shape)
# 	return event(addressEvent[:,2], addressEvent[:,1], addressEvent[:,0], addressEvent[:,3] * samplingTime)
