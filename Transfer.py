import logging
import os

import vtk
import SimpleITK as sitk
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import time
import qt

#
# Transfer Module
#

class Transfer(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Transfer"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Pedro Moreira BWH"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
        This module transfer images using openIGTLink
        """
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
        ...
        """

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#

def registerSampleData():
    """
    Add data sets to Sample Data module.
    """
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData
    iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # Transfer1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='Transfer',
        sampleName='Transfer1',
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, 'Transfer1.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames='Transfer1.nrrd',
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums='SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
        # This node name will be used when the data set is loaded
        nodeNames='Transfer1'
    )

    # Transfer2
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='Transfer',
        sampleName='Transfer2',
        thumbnailFileName=os.path.join(iconsPath, 'Transfer2.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames='Transfer2.nrrd',
        checksums='SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
        # This node name will be used when the data set is loaded
        nodeNames='Transfer2'
    )


#
# TransferWidget
#

class TransferWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/Transfer.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = TransferLogic()
    
        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)
        
        # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
        # (in the selected parameter node).
        self.ui.inputSelector1.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
        self.ui.inputSelector2.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

        self.ui.statusLabel.setStyleSheet("background-color: pink;border: 1px solid black;")
        self.ui.statusLabel.setText("No OpenIGTLink server")

        # Buttons
        self.ui.serverButton.connect('clicked(bool)', self.onServerButton)
        self.ui.sendButton.connect('clicked(bool)', self.onSendButton)
        self.ui.sendAuto.connect('clicked(bool)', self.onSendAutomaticButton)

        # Initialize OpenIGTLink Server and create connection observers
        if self.logic.openConnection():
            self.addObserver(self.logic.cnode, slicer.vtkMRMLIGTLConnectorNode.ConnectedEvent, self.onConnected)
            self.addObserver(self.logic.cnode, slicer.vtkMRMLIGTLConnectorNode.DisconnectedEvent, self.onDisconnected)
            self.addObserver(self.logic.cnode, slicer.vtkMRMLIGTLConnectorNode.DeactivatedEvent, self.onDeactivated)
        self.updateConnectionStatus()
        
        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()
        
        # Create OpenIGTLink Server node and connection observers
        #self.setServer()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        self.removeObservers(self.onConnected)
        self.removeObservers(self.onDisconnected)
        self.removeObservers(self.onDeactivated)
        self.logic.closeConnection()
        
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()
            self.logic.openConnection()

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())
        volumeNodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
       
        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.GetNodeReference("InputVolume1"):
            firstVolumeNode = volumeNodes.GetItemAsObject(0)
            if firstVolumeNode:
                self._parameterNode.SetNodeReferenceID("InputVolume1", firstVolumeNode.GetID())
        if not self._parameterNode.GetNodeReference("InputVolume2"):
            secondVolumeNode = volumeNodes.GetItemAsObject(1)
            if secondVolumeNode:
                self._parameterNode.SetNodeReferenceID("InputVolume2", secondVolumeNode.GetID())

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if inputParameterNode:
            self.logic.setDefaultParameters(inputParameterNode)

        # Unobserve previously selected parameter node and add an observer to the newly selected.
        # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
        # those are reflected immediately in the GUI.
        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        # Initial GUI update
        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        This method is called whenever parameter node is changed.
        The module GUI is updated to show the current state of the parameter node.
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
        self._updatingGUIFromParameterNode = True

        # Update node selectors and sliders
        self.ui.inputSelector1.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume1"))
        self.ui.inputSelector2.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume2"))

        # All the GUI updates are done
        self._updatingGUIFromParameterNode = False
        self.updateConnectionStatus() #TODO: Not sure where this should be done. Maybe add connection node to logic parameter list

    def updateParameterNodeFromGUI(self, caller=None, event=None):
        """
        This method is called when the user makes any change in the GUI.
        The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
        """

        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

        self._parameterNode.SetNodeReferenceID("InputVolume1", self.ui.inputSelector1.currentNodeID)
        self._parameterNode.SetNodeReferenceID("InputVolume2", self.ui.inputSelector2.currentNodeID)

        self._parameterNode.EndModify(wasModified)
                    
    def updateConnectionStatus(self):
        try:
            status = self.logic.cnode.GetState()
            if (status == slicer.vtkMRMLIGTLConnectorNode.StateOff):
                self.ui.statusLabel.setStyleSheet("background-color: pink; border: 1px solid black;")
                self.ui.statusLabel.setText("Server offline")
            elif (status == slicer.vtkMRMLIGTLConnectorNode.StateConnected):
                self.ui.statusLabel.setStyleSheet("background-color: lightgreen; border: 1px solid black;")
                self.ui.statusLabel.setText("Client connected... Ready to transfer!")
            elif (status == slicer.vtkMRMLIGTLConnectorNode.StateWaitConnection):
                self.ui.statusLabel.setStyleSheet("background-color: lightyellow; border: 1px solid black;")
                self.ui.statusLabel.setText("Server waiting for client")
            else:
                self.ui.statusLabel.setStyleSheet("background-color: pink; border: 1px solid black;")
                self.ui.statusLabel.setText("Error with OpenIGTLink server node")
        except:
            self.ui.statusLabel.setStyleSheet("background-color: pink; border: 1px solid black;")
            self.ui.statusLabel.setText("Error with OpenIGTLink server node")
            
    def onConnected(self, caller, event):
        self.updateConnectionStatus()
    
    def onDisconnected(self, caller, event):
        self.updateConnectionStatus()

    def onDeactivated(self, caller, event):
        self.updateConnectionStatus()

    def onSendAutomaticButton(self):
        print("sending automatic")
        self.ui.DirectoryButton.directory = os.path.join(os.path.dirname(__file__), 'images')
        if self.ui.sameFile.checkState()==0:
            self.logic.sendAuto(self.ui.DirectoryButton.directory,self.ui.transferRate.value)
        else:
            self.logic.sendAutoSameFile(self.ui.DirectoryButton.directory,self.ui.transferRate.value)

    #TODO: Define if this will be kept or removed for UI
    def onServerButton(self):
        if self.logic.openConnection():
            pass
        else:
            print('Could not Restart Server')
        self.updateConnectionStatus()

    def onSendButton(self):
        if self.logic.sendImages(self.ui.inputSelector1.currentNode(),self.ui.inputSelector2.currentNode()):
            print('- Images sent -\n')
        else:
            print("send button")

#
# TransferLogic
#

class TransferLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.

        if not parameterNode.GetParameter("Threshold"):
            parameterNode.SetParameter("Threshold", "100.0")
        if not parameterNode.GetParameter("Invert"):
            parameterNode.SetParameter("Invert", "false")

         """
        print('Logic module - Parameters initialization')

    def sendAutoSameFile(self,path,rate):
        #check number of files in the folder:
        files_all = os.listdir(path)

        #filter the data in case there are files that are not images
        list1 = ['name']
        files = [x for x in files_all if
                       all(y in x for y in list1)]
        num = len(files)
        files.sort()

        ##loadedVolume_M = slicer.util.loadVolume(os.path.join(path, files[0]))
        ##loadedVolume_P = slicer.util.loadVolume(os.path.join(path, files[1]))
        ##origin = loadedVolume_M.GetOrigin()
        if (num % 2) == 0:
            for i in range(0,num):
                if (i % 2) == 0:
                    # TODO: stop adding and removing nodes
                    ##reader = vtk.vtkNrrdReader()
                    ##reader.SetFileName(os.path.join(path, files[i]))
                    ##reader.Update()
                    ##loadedVolume_M.SetAndObserveImageData(reader.GetOutput())
                    ##loadedVolume_M.SetOrigin(origin)

                    ##reader1 = vtk.vtkNrrdReader()
                    ##reader1.SetFileName(os.path.join(path, files[i+1]))
                    ##reader1.Update()
                    ##loadedVolume_P.SetAndObserveImageData(reader1.GetOutput())

                    loadedVolume_M = slicer.util.loadVolume(os.path.join(path,files[i]))
                    loadedVolume_P = slicer.util.loadVolume(os.path.join(path,files[i+1]))
                    loadedVolume_M.SetName("Magnitude")
                    loadedVolume_P.SetName("Phase")
                    self.sendImages(loadedVolume_M,loadedVolume_P)
                    slicer.mrmlScene.RemoveNode(loadedVolume_M)
                    slicer.mrmlScene.RemoveNode(loadedVolume_P)
                    time.sleep(rate)
        else:
            print ("odd number of images!")


    def sendAuto(self,path,rate):
        #check number of files in the folder:
        files_all = os.listdir(path)

        #filter the data in case there are files that are not images
        list1 = ['name']
        files = [x for x in files_all if
                       all(y in x for y in list1)]
        num = len(files)
        files.sort()

        if (num % 2) == 0:
            for i in range(0,num):
                if (i % 2) == 0:
                    loadedVolume_M = slicer.util.loadVolume(os.path.join(path,files[i]))
                    loadedVolume_P = slicer.util.loadVolume(os.path.join(path,files[i+1]))
                    self.sendImages(loadedVolume_M,loadedVolume_P)
                    time.sleep(rate)
        else:
            print ("odd number of images!")

    # Send single pair of images
    def sendImages(self, image1, image2):
        if (self.cnode.GetState() == slicer.vtkMRMLIGTLConnectorNode.StateConnected):
            self.cnode.RegisterOutgoingMRMLNode(image2)
            self.cnode.PushNode(image2)
            time.sleep(0.1)
            self.cnode.UnregisterOutgoingMRMLNode(image2)
            self.cnode.RegisterOutgoingMRMLNode(image1)
            self.cnode.PushNode(image1)
            time.sleep(0.1)
            self.cnode.UnregisterOutgoingMRMLNode(image1)
            return True
        elif (self.cnode.GetState() == slicer.vtkMRMLIGTLConnectorNode.StateWaitConnection):
            print('Connection waiting for client')
            return False
        else:
            print('Connection not stablished yet')
            return False

    # Create OpenIGTLink Server Node, if not created already
    # Start server connection if not already running
    def openConnection(self):
        try:
            self.cnode = slicer.util.getNode('ImageTransferOIGTLServer')
            print('OpenIGTLink server node already exists')
        except:
            self.cnode = slicer.vtkMRMLIGTLConnectorNode()
            slicer.mrmlScene.AddNode(self.cnode)
            self.cnode.SetServerPort(18944)
            self.cnode.SetType(1)
            self.cnode.SetName('ImageTransferOIGTLServer')
        if (self.cnode.GetState() == slicer.vtkMRMLIGTLConnectorNode.StateOff):
            try:
                self.cnode.Start()
            except:
                print('Error starting OpenIGTLink server node')
                return False
        return True
            
    # Close server connection
    # Remove OpenIGTLink Server Node from mrmlScene
    def closeConnection(self):
        if self.cnode is not None:
            try:
                self.cnode.Stop()
                slicer.mrmlScene.RemoveNode(self.cnode)
                return True
            except:
                print('Error closing OpenIGTLink server node')
                return False
        

#
# TransferTest
#

class TransferTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_Transfer()

    def test_Transfer(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData
        registerSampleData()
        inputVolume1 = SampleData.downloadSample('Transfer1')
        inputVolume2 = SampleData.downloadSample('Transfer2')
        self.delayDisplay('Loaded test data set')

        # Test the module logic

        logic = TransferLogic()
        # TODO: Push sample data to OpenIGTLink Server
        if logic.openConnection():
            self.delayDisplay('Created server')
            clientTimeout = 0
            while True:
                if (logic.cnode.GetState() != slicer.vtkMRMLIGTLConnectorNode.StateConnected):
                    time.sleep(0.1)
                    if (clientTimeout <= 100):
                        clientTimeout += 1
                        continue # Return to loop
                    else: 
                        self.delayDisplay('Client connection timeout')
                        break   # Timeout
                # Client connected
                if logic.sendImages(inputVolume1, inputVolume2):
                    self.delayDisplay('Test passed')
                    break
