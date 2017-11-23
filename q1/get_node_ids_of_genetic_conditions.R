library(RNeo4j)

neo4j_password <- read.table("../../database_password_do_not_check_into_github.txt", stringsAsFactors=FALSE)$V1

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
genetic_conditions_MIM_numbers <- omim_data_genetic_conditions$MIM_number
                               
graph <- RNeo4j::startGraph("http://ncats.saramsey.org:7474/db/data",
                             username="neo4j",
                             password=neo4j_password)

res <- pbapply::pblapply(genetic_conditions_MIM_numbers,
                  function(MIM_number) {
                      mim_id <- setNames(unlist(cypher(graph,
                                                       sprintf("MATCH (n:disease) WHERE n.iri=\"http://purl.obolibrary.org/obo/OMIM_%d\" RETURN ID(n)",
                                                               MIM_number))),NULL)
                      if (! is.null(mim_id)) {
                          mim_id
                      } else {
                          NA
                      }
                  })

omim_data_genetic_conditions_export <- data.frame(omim_data_genetic_conditions,
                                                  neo4j_id=unlist(res),
                                                  stringsAsFactors=FALSE)

write.table(subset(omim_data_genetic_conditions_export, ! is.na(neo4j_id)),
            file="Genetic_conditions_from_OMIM_with_Neo4j_node_IDs.txt",
            sep="\t",
            row.names=FALSE,
            col.names=TRUE,
            quote=FALSE)

