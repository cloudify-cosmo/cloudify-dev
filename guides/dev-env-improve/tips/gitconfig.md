## Config Git Enviourment ##

Use the following lines in order to configure your git enviourment.
Just set it as the ~/.gitconfig content


```
[color]
        ui = auto
        branch = auto
        diff = auto
        interactive = auto
        status = auto
[user]
        name = [Your full name]
        email = [Your Email]
[alias]
        lg = log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit
        lola = log --graph --decorate --pretty=oneline --abbrev-commit --all

[core]
        autocrlf = input
```