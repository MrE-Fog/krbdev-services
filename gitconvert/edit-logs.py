# Python script to edit log messages in the krb5 repository to look
# better in git.  Message transformations include:
#
# * Move RT headers to the end of the message.
# * If the RT headers contain a subject, put it at the beginning as a
#   summary line.
# * Normalize CR and CRLF newlines, eliminate leading and trailing
#   blank lines, and always end the message with a newline.
# * If there is a summary line, strip off any trailing period.
#
# Requires Python 2.7 for subprocess.check_output.  Requires svnlook
# and svnadmin in the path.

import re
import string
import subprocess
import sys
import tempfile

header_re = re.compile('([\w-]+):\s*(.*)')
newline_re = re.compile('\r\n|\r|\n')
def edit_msg(msg):
    # Split the message into lines.  This will translate CR and CRLF
    # line endings to LF when we re-join the lines at the end.
    lines = newline_re.split(msg)

    # Remove RT headers.  Remember the subject if we see one.
    headers = []
    subject = None
    while len(lines) > 0:
        m = header_re.match(lines[0])
        if not m:
            break
        if m.group(1).lower() == 'subject':
            subject = m.group(2)
        headers.append(lines[0])
        del lines[0]

    # Strip leading and trailing blank lines.
    while len(lines) > 0 and lines[0] == '':
        del lines[0]
    while len(lines) > 0 and lines[-1] == '':
        del lines[-1]

    # Put RT headers back at the end of the message, separated by a
    # blank line (but omit the blank line if there's nothing but
    # headers).
    if headers:
        lines = lines + (lines and ['']) + headers

    # If we captured a subject, put it in the start as a summary.
    if subject:
        lines = [subject, ''] + lines

    # Trim sentence-ending period on summary line.
    if (len(lines) > 0 and lines[0].endswith('.') and
        (len(lines) == 1 or lines[1] == '')):
        lines[0] = lines[0][:-1]

    # End the log message with a newline, even if the old one didn't.
    return string.join(lines, '\n') + '\n'


if len(sys.argv) != 2:
    print "Usage: edit-logs.py repository-path"
    sys.exit(1)
repo = sys.argv[1]
lastrev = int(subprocess.check_output(['svnlook', 'youngest', repo]))

for rev in range(1, lastrev + 1):
    try:
        msg = subprocess.check_output(['svnlook', 'pg', repo, '--revprop',
                                       '-r', str(rev), 'svn:log'])
    except CalledProcessError:
        continue
    newmsg = edit_msg(msg)
    if newmsg != msg:
        f = tempfile.NamedTemporaryFile()
        f.write(newmsg)
        f.flush()
        subprocess.check_call(['svnadmin', 'setrevprop', repo, '-r', str(rev),
                               'svn:log', f.name])
        f.close()