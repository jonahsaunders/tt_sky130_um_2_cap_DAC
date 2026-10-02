"""Hardware-neutral controller: callbacks must produce real, timed 1.8 V signals."""
def write_code(code, set_phases, delay_us):
    if not isinstance(code,int) or not 0<=code<=255:raise ValueError('code must be 0..255')
    set_phases(False,True,True);delay_us(8)
    set_phases(False,False,False);delay_us(.2)
    for bit in range(8):
        one=bool(code & (1<<bit));set_phases(one,not one,False);delay_us(2)
        set_phases(False,False,False);delay_us(.2)
        set_phases(False,False,True);delay_us(2)
        set_phases(False,False,False);delay_us(.2)
    delay_us(3)
    # The output may now be sampled. An additional 0.5 us gap gives 46.9 us/word.

def code_for_voltage(target_v, measured_code0_v, measured_code255_v):
    """Two-point calibration; targets must lie inside measured endpoint range."""
    if not measured_code0_v<=target_v<=measured_code255_v:raise ValueError('target outside calibrated range')
    slope=(measured_code255_v-measured_code0_v)/255
    return max(0,min(255,round((target_v-measured_code0_v)/slope)))
