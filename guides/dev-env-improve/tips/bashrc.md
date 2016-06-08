## Config Shell Enviourment ##

In order to config the shell enviourment, we'll modify the ~/.bashrc file. You may want to create a backup for your current file.
After you've created a backup, just add the following lines at the end of the file.



```
# display current git branch 
function parse_git_branch() {
	RED="\[\033[1;31m\]"
	GREEN="\[\033[1;32m\]"
	RESET_COLOR='\[\e[0m\]'

	if ! git rev-parse --git-dir > /dev/null 2>&1; then
		echo "${RESET_COLOR}$ "
		return 0
	fi
	git_branch=$(git branch 2>/dev/null| sed -n '/^\*/s/^\* //p')
	git status | grep "nothing to commit" > /dev/null 2>&1
	if [[ ${?} == 0 ]]; then
		echo "${GREEN}($git_branch)\[\033[00m\] ${RESET_COLOR}$ " 
	else
		echo "${RED}($git_branch)\[\033[00m\] ${RESET_COLOR}$ "
	fi
}

# update shell prompt
function __prompt() {
	if ${use_color} ; then
		# Enable colors for ls, etc.  Prefer ~/.dir_colors #64489
		if type -P dircolors >/dev/null ; then
			if [[ -f ~/.dir_colors ]] ; then
				eval $(dircolors -b ~/.dir_colors)
			elif [[ -f /etc/DIR_COLORS ]] ; then
				eval $(dircolors -b /etc/DIR_COLORS)
			fi
		fi

		if [[ ${EUID} == 0 ]] ; then
			PS1='${debian_chroot:+($debian_chroot)}\[\033[01;31m\]\h\[\033[01;34m\] \W \$\[\033[00m\] '
			PS1+=" ${RESET_COLOR}$ "
		else
			#PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[01;34m\] \w \$\[\033[00m\] '
			PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[01;34m\] \w '
		        PS1+=$(parse_git_branch)
		fi

		alias ls='ls --color=auto'
		alias grep='grep --colour=auto'
	else
		if [[ ${EUID} == 0 ]] ; then
			# show root@ when we don't have colors
			PS1='\u@\h \W \$ '
		else
			PS1='\u@\h \w \$ '
		fi
	fi

	# add venv info
	if [ "`basename \"$VIRTUAL_ENV\"`" = "__" ] ; then
        # special case for Aspen magic directories
        # see http://www.zetadev.com/software/aspen/
        PS1="[`basename \`dirname \"$VIRTUAL_ENV\"\``] $PS1"
    elif [ "$VIRTUAL_ENV" != "" ]; then
        PS1="(`basename \"$VIRTUAL_ENV\"`) $PS1"
    fi

}
PROMPT_COMMAND=__prompt

# Try to keep environment pollution down, EPA loves us.
unset use_color safe_term match_lhs
```