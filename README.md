# Blender Addon: MTS Collisions Exporter

## A Blender addon for 2.79 and 2.8X and above to easily set up collision boxes and door hitboxes for MTS/IV vehicles within Blender and export it as a json

### Credits: Turbo Defender | Gyro Hero | Laura Darkez

# Instructions:

## 1. Installation
  
  1.1. Installing the addon (2.79)
  
    1.1.1. File —> User Preferences —> Add-ons
    
    1.1.2. On the bottom of the window, click on "Install Add-on from file"
    
    1.1.3. Select the "mts_collision_exporter_2-79.py" file and click install

  1.2. Installing the addon (2.8 and above)
  
    1.2.1. Edit —> Preferences —> Add-ons

    1.2.2. On the top of the window, click on "Install..."
    
    1.2.3. Select the "mts_collision_exporter_2-8X_2-9X.py" file and click install
  
## 2. Using the addon (2.79 above)
  
  2.1. Navigating to the panel
    
    2.1.1. Create a cube
    
    2.1.2. Go to the "Object Properties tab"
      
   In 2.79
      
   ![2.79](https://i.imgur.com/mhNyV1f.png)
      
   In 2.8 and above
      
   ![2.8+](https://i.imgur.com/aP8EOoi.png)
  
    2.1.3. Scroll down until you find the "MTS/IV Collision Properties"
   
   In 2.79
      
   ![2.79](https://i.imgur.com/oPdoLJw.png)
      
   In 2.8 and above
      
   ![2.8+](https://i.imgur.com/DAakV2Y.png)
   
  2.2. Making collisions
    
    2.2.1. With the cube selected click on the "Collision" checkbox, in the "Collision Box Properties" sub-pane, to set it as true. 
    There you go! You have a cube marked as a collision box
    
    2.2.2. Set the collision box's properties as you wish.
    
    2.2.3. Scale the cube to your liking. If the x and y dimensions are not the same, the box will automatically be divided into boxes the size of whichever side is shorter.
    
          [OR]
          
          Scale the cube to cover the area you want, and set the subdivision width and height to subdivide the cube into multiple collision boxes of that size, that span the covered area
    
    2.2.4. If you want the boxes to be on a diagonal, rotate the cube in the desired direction WHILE IN OBJECT MODE (NOT EDIT MODE)
    
    2.2.5. Click on "Export Collisions" and save the file (I hope you know what to do after this)
    
  2.3. Making doors
  
    2.3.1. With the cube selected click on the "Door" checkbox, in the "Door Collision Properties" sub-panel, to set it as true. Now you have a cube marked as a door box
    
    2.3.2. Set the door's properties as you wish.
    
    2.3.3. Scale the cube to your liking, but make sure that the X and Y dimensions are the same.
          
          Note: Subdivision on the door box doesn't work yet
          
    2.3.4. Make a new cube or duplicate the existing cube. Next click on the previous cube and go to the "Open Pos Box" object selector, and selected the newly made cube.
    
    2.3.5. Position the new cube as you like. DON'T TOUCH THE DOOR OR COLLISION PROEPERTIES OR IT'LL BUG OUT!
    
    2.3.6. Click on "Export Collisions" and save the file. This will export both the collisions and doors together.
