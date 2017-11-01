omim_data <- read.table("mimTitles.txt",
                        sep="\t",
                        comment.char="#",
                        stringsAsFactors=FALSE,
                        quote="",
                        fill=TRUE)
names(omim_data) <- c("prefix", "MIM_number", "preferred_title", "alternative_title", "symbols")

omim_data_genetic_conditions <- subset(omim_data,
                                       prefix != "Asterisk" &
                                       prefix != "Plus" &
                                       prefix != "Caret")


write.table(omim_data_genetic_conditions,
            file="Genetic_conditions_from_OMIM.txt",
            sep="\t",
            row.names=FALSE,
            col.names=TRUE,
            quote=FALSE)


