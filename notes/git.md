# RTX project Git cheat sheet 

## Contributors:  David Koslicki

# create new branch
   
go to master branch

    git checkout master
    
get most up to date copy

    git pull origin master 
    
create feature branch

    git checkout -b my-new-feature-branch

# Commit to new branch

to make sure you are on the feature branch, make sure the * is next to the
feature branch, otherwise use git checkout my-new-feature-branch

    git branch
    
commit all changes to feature branch, write commit message:

    git commit -a

to make sure you have the most up to date version locally:

    git pull origin NewStdAPI 

push all changes to github:

    git push origin NewStdAPI 

# Merge new code from master into feature branch
Note: Make sure you have the most up to date version locally

go to master branch:

    git checkout master
    
get up to date copy, or git pull origin master depending on your settings

    git pull 
    
# merge from master into feature branch

go to feature branch:

    git checkout my-new-feature-branch

merge from master to feature:

    git merge --no-ff origin/master

push changes to github:

    git push origin my-new-feature-branch
