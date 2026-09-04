import sigrity

bbsprj = sigrity.get_bbsproject()
BbsOptSettings = bbsprj.BbsOptionSettings
BbsOptSettings.set_extraction_mode('Precision mode')
BbsOptSettings.set_extraction_mode('Passivity mode II')
BbsOptSettings.enable_sparameter_smoothing_matrix(True)
BbsOptSettings.set_sparameter_smoothing_fitting_type(2)
BbsOptSettings.set_sparameter_smoothing_fitting_type(1)
BbsOptSettings.set_sparameter_smoothing_fitting_type(0)
BbsOptSettings.set_sparameter_smoothing_matrix_type('All matrix entries')
BbsOptSettings.set_sparameter_smoothing_matrix_type('Diagonal matrix entries')