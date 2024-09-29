import maya.cmds as cmds
import maya.mel as mel
from functools import partial

#--------------------------------------------------------------------
def updateField(*args):
    slider = cmds.intSlider('falloff_slider', q=True, value=True)
    cmds.intField('falloff_field', edit=True, value=slider)

def updateSlider(*args):
    field = cmds.intField('falloff_field', q=True, value=True)
    cmds.intSlider('falloff_slider', edit=True, value=field)

def enableFalloff(*args):
    menu = cmds.optionMenu('falloff_menu', q=True, sl=True)
    if menu == 1:
        cmds.intSlider('falloff_slider', edit=True, enable=False)
        cmds.intField('falloff_field', edit=True, enable=False)
    else:
        cmds.intSlider('falloff_slider', edit=True, enable=True)
        cmds.intField('falloff_field', edit=True, enable=True)

def getDropdownMenu(menu, *args):

    menuSelection = cmds.optionMenu(menu, q=True, select=True)
    return menuSelection

#--------------------------------------------------------------------
def closestInt(list, target_value):

    closest_value = None
    closest_index = -1 
    smallest_difference = float('inf') # Start with an infinitely large number

    for index, value in enumerate(list):
        difference = abs(value - target_value) # Calculate the absolute difference from target value

        # Update variables is absolute difference is smaller than previous smallest difference
        if difference < smallest_difference:
            smallest_difference = difference
            closest_value = value
            closest_index = index

    return closest_value, closest_index

#--------------------------------------------------------------------
def getSelection():

    ctrl = cmds.ls(sl=True) # Get veiwport selection
    
    # check for active selection
    if not ctrl:
        cmds.inViewMessage(amg='<font color = yellow>Please select one or more controllers.', pos='midCenter', fade=True) # Viewport message for user 
        print('__ERROR -- Nothing selected -- ERROR__') # Debug log
    else:
        print(f'__Selection: {ctrl}')
        return ctrl # Publish ctrl selection 

#--------------------------------------------------------------------
def getChannels(ctrl):

    curves = cmds.keyframe(ctrl, q=True, n=True) # Get all channelBox curve names as a list
    channels = [item.rsplit('_', 1)[-1] for item in curves] # Isolate channels from long names

    return channels # Publish channels list

#--------------------------------------------------------------------
def getSelectedRange(): # Get the highlighted range on the timeline

    # Get scene timeline range
    scene_start_frame = cmds.playbackOptions(q=True, animationStartTime=True)
    scene_end_frame = cmds.playbackOptions(q=True, animationEndTime=True)

    # Get selected timeline range
    aTimeSlider = mel.eval('$tmpVar=$gPlayBackSlider') # Mel command to identify the timeline
    selected_range = cmds.timeControl(aTimeSlider, q=True, rangeArray=True) # Python command to check for the selected range 

    difference = selected_range[1] - selected_range[0] # Check to see if the timeline is highlighted by verifying that the diffrence between the start and end of the selected range is greater than 1

    # If timeline section not slected, set the selected range to the timeline length 
    if difference == 1:
        selected_range = [scene_start_frame, scene_end_frame]
    else:
        selected_range = selected_range

    # Debug Log:
    print('------------------------------------------')
    print(f'__Selected Range: {selected_range}')
    print('------------------------------------------')

    return selected_range # Publish the frame range

#--------------------------------------------------------------------
def getKeyframeInfo(ctrl, target, selected_range):

    anim_curve = cmds.findKeyframe(ctrl, curve=True, at=target) # Get animation curve
    key_index = cmds.keyframe(anim_curve, q=True, time=(selected_range[0], selected_range[1]), indexValue=True) # Get the indeces of keyframes on the curve
    key_times = cmds.keyframe(anim_curve, q=True, index=(key_index[0], key_index[-1]))
    key_quantity = len(key_index) # Get the number of keys being targeted

    # Get the value of each keyframe on the designated animation curve
    keyframe_values = []
    for n in enumerate(key_index):
        x = cmds.keyframe(anim_curve, q=True, eval=True, index=(n[1],))[0]
        keyframe_values.append(x)

    # Debug Log:
    print('------------------------------------------')
    print(f'__Animation Curve: {anim_curve[0]}')
    print(f'__Number of Keys: {key_quantity}')
    print(f'__Key Times: {key_times}')
    print(f'__Key Indeces: {key_index}')
    print(f'__Key Values: {keyframe_values}')
    #print('------------------------------------------')

    return anim_curve, key_index, key_times, key_quantity, keyframe_values # Publish curve information

#--------------------------------------------------------------------
def getAdjustmentValue(keyframe_values, key_index, key_quantity):

    # Query UI for forwards Adjustment button status
    if cmds.radioButton('forward_button', q=True, sl=True) == False:
        key_index.reverse()
        keyframe_values.reverse()
        print('\nBackwards Adjustment. key_index list reversed.')
    else:
        print('Forwards Adjustment. No list reversals necessary.')

    adjustment_value = keyframe_values[0] - keyframe_values[1] # Find the difference between the first two keys

    # Debug Log:
    print('')
    print(f'__Adjustment Value: {adjustment_value}')

    return adjustment_value, key_index, keyframe_values # Publish adjustment values

#--------------------------------------------------------------------
def defineFalloffRange(key_times, key_index):

    key_times.pop(0)
    key_index.pop(0)

    slider_percentage = cmds.intSlider('falloff_slider', q=True, value=True) / 100
    new_start_time = (key_times[-1] - key_times[0]) * slider_percentage
    new_start_time = key_times[0] + new_start_time

    closest_value, closest_index = closestInt(key_times, new_start_time)

    adjusted_key_times = key_times[closest_index:]
    adjusted_key_index = key_index[closest_index:]

    # Debug Log:
    print('')
    print(f'__Slider Percentage: {slider_percentage}')
    print(f'__New Start Time: {new_start_time}')
    print(f'__Closest Value and Index: {closest_value}  -  {closest_index}')
    print(f'__Key Times:          {key_times}')
    print(f'__Adjusted Key Times: {adjusted_key_times}')
    print(f'__Key Indeces:          {key_index}')
    print(f'__Adjusted Key Indeces: {adjusted_key_index}')

    return closest_index

#--------------------------------------------------------------------
def falloff(adjustment_value, key_times, closest_index, menuSelection):
    
    modifier_values = [] # Create empty list to store falloff values
    pre_falloff_modifier_values = []

    # Failsafe
    if closest_index == len(key_times) - 1: # If the falloff start key is the last key in the list
        print('\nNot enough keys to create falloff')
        for i in key_times:
            modifier_values.append(adjustment_value)
        return modifier_values
    
    # Failsafe
    if menuSelection == 1: # If falloff menu is set to "None"
        print('\nFalloff disabled')
        for i in key_times:
            modifier_values.append(adjustment_value)
        return modifier_values

    # split key_times for falloff adjustment
    left_split_key_times = key_times[:closest_index]
    right_split_key_times = key_times[closest_index:]

    # Replace left_split_key_times with adjustment_value
    for i in left_split_key_times:
        pre_falloff_modifier_values.append(adjustment_value)

    total_length = right_split_key_times[-1] - right_split_key_times[0] # Calculate time span 

    for i, data in enumerate(right_split_key_times):
        relative_position = (data - right_split_key_times[0]) / total_length # Calculate relative position (normalized 0 to 1)

        # Menu fallof curves
        if menuSelection == 2: # Linear
            falloff_value = adjustment_value * (1 - relative_position) # Calculate how much to subtract (full modifier at first point, 0 at last)
        if menuSelection == 3: # Quadratic 
            falloff_value = adjustment_value * (1 - relative_position) ** 2
        if menuSelection == 4: # Reverse Quadratic
            falloff_value = adjustment_value * (1 - relative_position ** 2) 
        modifier_values.append(falloff_value)

    # combine the two lists
    modifier_values = pre_falloff_modifier_values + modifier_values

    # Debug Log:
    print('')
    print(f'__Split List - Key Times: {left_split_key_times} - {right_split_key_times}')
    print(f'__Modified Values: {modifier_values}')
    print('------------------------------------------')

    return modifier_values

#--------------------------------------------------------------------
def execute(*args):

    # Get selected controllers
    ctrl = getSelection()
    # End process if no selection exists
    if not ctrl:
        return
    
    # Get slected Timeline Range
    selected_range = getSelectedRange()

    # Get falloff menu 
    menuSelection = getDropdownMenu('falloff_menu', *args)

    # Run through each controller in ctrl
    for x in ctrl: 
        channels = getChannels(x)

        # Run through functions for each axes
        for i in channels:
            try:
                anim_curve, key_index, key_times, key_quantity, keyframe_values = getKeyframeInfo(x, i, selected_range)
            except:
                print(f'{x} has no channel for {i}')
            
            adjustment_value, key_index, keyframe_values = getAdjustmentValue(keyframe_values, key_index, key_quantity)

            closest_index = defineFalloffRange(key_times, key_index)

            modifier_values = falloff(adjustment_value, key_times, closest_index, menuSelection)

            for i, value in enumerate(modifier_values):
                cmds.keyframe(anim_curve, edit=True, index=(key_index[i], key_index[i]), valueChange=value, relative=True)

#------------------------------------------
# POP UP WINDOW
#------------------------------------------
def instructions(*args):
    
    instructionWindow = cmds.window(title='Instructions', widthHeight=(340, 200), s=True, mnb=False, mxb=False)
        
    instructionLayout = cmds.columnLayout(adj=True)
    
    cmds.setParent(instructionLayout)
    cmds.separator(style='none', h=10)
    cmds.rowColumnLayout(numberOfColumns=2, columnSpacing=(1,10))
    cmds.text(l='''1. Duplicate the Keyframe you would like to adjust, and position it to the left in your timeline.<br><br>
            2. Adjust pose.<br><br>
            3. Select all affected controllers.<br><br>
            4. Select the desired timeslider region, starting with the modified keyframe. If timeslider not selected, changes will occur on the entire range.<br><br>
            5. Execute.
            ''', al='left', ww=True)
    cmds.text(l='')
    
    cmds.showWindow(instructionWindow)

#------------------------------------------
# UI WINDOW 
#------------------------------------------
window = cmds.window(title='Pose Adjuster', widthHeight=(225, 225), s=False, mnb=False, mxb=False)

autographLayout = cmds.columnLayout(adj=True)
runLayout = cmds.columnLayout(adj=True)
sliderLayout = cmds.columnLayout(adj=True)
optionLayout = cmds.columnLayout(adj=True)
helpLayout =cmds.columnLayout(adj=True)

#------------------------------------------
cmds.setParent(helpLayout)
cmds.separator(style='none', h=2)
helpButton = cmds.button(l='Instructions', c=(instructions))
cmds.separator(style='none', h=10)

#------------------------------------------
cmds.setParent(optionLayout)

cmds.rowColumnLayout(numberOfColumns=4)
cmds.text(l='   <-- Backwards  ')
cmds.radioCollection()
cmds.radioButton(l='  ')
cmds.radioButton('forward_button', l='', sl=True)
cmds.text(l='  Forwards -->')

#------------------------------------------
cmds.setParent(sliderLayout)

cmds.separator(style='in', h=15)

cmds.rowColumnLayout(numberOfColumns=1, cs=(1,10))
cmds.optionMenu('falloff_menu', l='Falloff: ', changeCommand=enableFalloff)
cmds.menuItem( label='None' )
cmds.menuItem( label='Linear' )
cmds.menuItem( label='Quadratic' )
cmds.menuItem( label='Reverse Quadratic' )

cmds.separator(style='none', h=10)
cmds.text(l='Start Position:', align='left')
cmds.separator(style='none', h=5)

cmds.rowColumnLayout(numberOfColumns=2, cs=(2,10))
cmds.intField('falloff_field', width=35, value=50, enable=False, changeCommand=updateSlider)
cmds.intSlider('falloff_slider', min=1, max=100, value=50, width=130, enable=False, changeCommand=updateField)

#------------------------------------------
cmds.setParent(runLayout)

cmds.separator(style='in', h=20)
cmds.button(l='Execute', c=partial(execute))

#------------------------------------------
cmds.setParent(autographLayout)

cmds.text(l='Tool built by Emile Menard', font="smallFixedWidthFont", enable=False, h=20)

#------------------------------------------

cmds.showWindow(window)