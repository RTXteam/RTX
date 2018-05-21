.load ./spellfix
CREATE TABLE dict (str Text);
.import "./nodeNames.tmp" dict
.import "./questions.tmp" dict
CREATE UNIQUE INDEX dict_idx ON dict(str);
CREATE VIRTUAL TABLE spell USING spellfix1;
INSERT INTO spell(word) SELECT str FROM dict;
