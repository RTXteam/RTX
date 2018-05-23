.load ./spellfix
CREATE TABLE dict (rank INTEGER, str Text);
.separator "\t"
.import "./nodeNames.tmp" dict
.import "./questions.tmp" dict
.import "./uni.tmp" dict
.import "./bi.tmp" dict
CREATE UNIQUE INDEX dict_idx ON dict(str);
CREATE VIRTUAL TABLE spell USING spellfix1;
INSERT INTO spell(word,rank) SELECT str, rank FROM dict;
