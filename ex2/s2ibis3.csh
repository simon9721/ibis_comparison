#!/bin/csh -f

# This is the startup script for s2ibis3 on Unix.
# See the usage below for more info. 

@ i = 1
while($i <= $#argv)
  switch($argv[$i])
    case "-root":
      @ i = $i + 1
      set rootdir = "$argv[$i]"
      set javadir = "$rootdir""/java"

      breaksw
    case "-s2ibis3":
      @ i = $i + 1
      set s2ifile = "$argv[$i]"
      breaksw
    default:
      goto usage
      breaksw
  endsw
  @ i = $i + 1
end

# Getting ready to run s2ibis3 - search for a Java interpreter
#if (! -d java) goto dirmissing
set javaprog = "`which java`"
if(! -x "$javaprog") set javaprog = "`which jre`"
if(! -x "$javaprog") goto javamissing

# Check the Java version - we require at least 1.4
# |& pipes the stdout to the 'grep' program. || is the logical 'OR'
$javaprog -version |& grep "java version.*1\.4" || goto javaversion

# Run the s2ibis3 utility
echo "Running Java"
$javaprog -cp $javadir s2ibis3 $s2ifile |& tee s2ibis3.log 
set retval1 = $status

grep "Unable to open" s2ibis3.log
set retval2 = $status

grep "Error in running" s2ibis3.log
set retval3 = $status

if ($retval3 == 0) then 
goto missingengine
else if ($retval2 == 0) then 
goto missingfile
else if ($retval1 != 0) then 
goto javaerror
else 
echo "Run Complete"
endif

goto thanks
exit 0

dirmissing:
echo ""
echo "Installation error."
echo "This script must be run in the s2ibis3 installation directory."
echo "Alternatively you could use the '-root' switch and specify the "
echo "installation directory."
echo ""
exit 1

javaerror:
java -version
echo ""
echo "An error occured running the Java program."
echo "If the Java version above is less than 1.4, please install Java 2, ver 1.4."
echo ""
exit 2

javamissing:
echo ""
echo "Java is required, but not installed. Please install Java 2, ver 1.4."
echo ""
exit 3

javaversion:
java -version
echo ""
echo "The installed Java is not version 1.4.X. Please install Java 2, ver 1.4."
exit 4

usage:
echo ""
echo "To start the s2ibis3 utility:"
echo "s2ibis3.csh [-root <rootDir>] -s2ibis3 <*.s2i s2iFile> "
echo ""
echo "The -root option may be needed to tell s2ibis3 where it's files are located"
echo ""
exit 0

missingfile:
echo ""
echo "A file needed to run s2ibis3 is missing."
echo "Check s2ibis3.log to get more information."
echo ""
exit 5

missingengine:
echo ""
echo "A spice engine needed to run s2ibis3 is missing."
echo "Check s2ibis3.log to get more information."
echo ""
exit 5

thanks:
echo S2IBIS3, 2005. North Carolina State University.
echo ""
exit 0
