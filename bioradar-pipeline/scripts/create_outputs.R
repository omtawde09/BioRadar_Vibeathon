# R script to output the final tables

# conda activate amplicon-r

# Read in asv table
asv_table <- read.delim("./qiime2/12S/asvs/asv-table.tsv", header=TRUE, row.names=NULL, 
    stringsAsFactors=FALSE, na.strings = "n/a", skip = 1)
names(asv_table)[1] <- "Feature.ID"
head(asv_table)
##                        Feature.ID X01.BWL.D.MR8 X02.BWL.D.MR8 X03.BWL.U.MR7
##1 4cea7a2c586ece5f6fd34f0f4b7ca549         17415         22063         13520
##2 ab57e27073e171e129ad22dd3255ef90          2448          4255          2880
##3 c0401f654f64b5f049290cde7b7a5324             0             0            58
##4 db052692a52f3108d0c5b9d88183e82f           103             0            48
##5 66fc64121e9a1ceda4d83b985e125b8f            39             0            55
##6 51c497f633bd00f84a46a8d8f7e7ac2e             0             0             0
##  X04.BWL.U.MR7 X05.BWL.1 X06.BWL.1 X07.BWL.1 X08.BWL.8 X09.BWL.8 X10.BWL.8#
##1         31729     23114     21346     17669     13502     23001     14497
##2          6920      4887      4943      2903      2674      5134      1945
##3             0        80         0       132         0         0         0
##4            75        45        54         0        51       116         0
##5           126         0         0        89         0        50        16
##6             0         0         6        32         0        16        34
##  X11.GC.3 X12.GC.3 X13.GC.3 X14.GUS.3 X15.GUS.3 X16.GUS.3 X17.RBD.3 X18.RBD.3
##1    16991    20463    13005     22562     17095     25691     24447     14157
##2     3203     4318     1696      4693      4090      2777      4602      2874
##3        0        0        0         0         0        56         0       172
##4        0      168        0         0         0        80         0        26
##5        0       43        0         0        46        81        39         0
##6        0       22        0         0        26        44         0         0
####
midori <- read.delim('./qiime2/12S/asvs/Midori_trained_taxonomy.tsv', header=TRUE, row.names=NULL)

##head(midori)
##                        Feature.ID
##1 4cea7a2c586ece5f6fd34f0f4b7ca549
##2 ab57e27073e171e129ad22dd3255ef90
##3 c0401f654f64b5f049290cde7b7a5324
##4 db052692a52f3108d0c5b9d88183e82f
##5 66fc64121e9a1ceda4d83b985e125b8f
##6 51c497f633bd00f84a46a8d8f7e7ac2e
##                                                                                                                                                                 Taxon
##1           k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##2           k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##3                                            k__Eukaryota_2759;p__Chordata_7711;c__Mammalia_40674;o__Primates_9443;f__Hominidae_9604;g__Homo_9605;s__Homo sapiens_9606
##4 k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Maccullochella_135758;s__Maccullochella peelii_135761
##5      k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria australasica_135765
##6                           k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Cypriniformes_7952;f__Cyprinidae_7953;g__Cyprinus_7961;s__Cyprinus carpio_7962
##  Confidence
##1  1.0000000
##2  0.9999999
##3  0.9957852
##4  0.9977458
##5  1.0000000
##6  0.9530607

names(midori)[2:3] <- paste("midori", names(midori)[2:3], sep="_")

output <- merge(asv_table, midori, by="Feature.ID")
head(output)
##                        Feature.ID X01.BWL.D.MR8 X02.BWL.D.MR8 X03.BWL.U.MR7
##1 0141c63e4e0e71ab8407a5e1c4507334             0             0             0
##2 01dea82e257a4bff7ab243c1091841ec             0             0             0
##3 0208e84f3960c9d1cbfe1bdbbb9b8656             0             0             0
##4 023b29c8883be387e7f03d94f3a86d80             0             0             0
##5 028cd8e4c842caa082607fac05fc04e9            22             0             0
##6 02ba8f13b19e4ca2a03aa22b18bfa150             0             0             0
##  X04.BWL.U.MR7 X05.BWL.1 X06.BWL.1 X07.BWL.1 X08.BWL.8 X09.BWL.8 X10.BWL.8
##1             0         0         0         0         0         0         0
##2             0         0         0         0         0         0         0
##3             0         0        89         0         0         0         0
##4             0         0         0         0         0         0         0
##5             0         0         0         0         0         0         0
##6             0         0         0         0         0         0         0
##  X11.GC.3 X12.GC.3 X13.GC.3 X14.GUS.3 X15.GUS.3 X16.GUS.3 X17.RBD.3 X18.RBD.3
##1        0        0        0         0         0         0         0         0
##2        0        0        0         0         0         0         0         0
##3        0        0        0         0         0         0         0         0
##4        0        0        0         0         0         0         0         0
##5        0        0        0         0         0         0         0         0
##6        0        0        0         0         0        30         0         0
##  X19.RBD.3 X20.HDS.3 X21.HDS.3 X22.HDS.3 X23.MF.3 X24.MF.3 X25.MF.3 X26.HW.3
##1         0         0         0        56        0        0        0        0
##2         0         0         0         0        0        0        0       32
##3        0         0         0         0        0        0        0        0
##4         0         0         0         0       82        0        0        0
##5         0         0         0         0        0        0        0        0
##6         0         0         0         0        0        0        0        0
##  X27.HW.3 X28.HW.3 X29.MIN.1 X30.MIN.1 X31.MIN.1 X32.MS.1 X33.MS.1 X34.MS.1
##1        0        0         0         0         0        0        0        0
##2        0        0         0         0         0        0        0        0
##3       0        0         0         0         0        0        0        0
##4        0        0         0         0         0        0        0        0
##5        0        0         0         0         0        0        0        0
##6       0        0         0         0         0        0        0        0
##  X35.MS.1
##1        0
##2        0
##3        0
##4        0
##5        0
##6        0
                                                                                                                                                  ##midori_Taxon
##1   k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##2   k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##3   k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##4   k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##5 k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Gadopsis_135753;s__Gadopsis bispinosus_135754
##6   k__Eukaryota_2759;p__Chordata_7711;c__Actinopteri_186623;o__Centrarchiformes_1489940;f__Percichthyidae_8162;g__Macquaria_45782;s__Macquaria ambigua_135764
##  midori_Confidence
##1         0.9999856
##2         0.9999982
##3         0.9997888
##4         0.9996141
##5        0.9861425
##6         0.9999984



write.table(output, file="./qiime2/12S/asvs/asv_count_tax.tsv", quote=FALSE, sep="\t", row.names=FALSE)

#> sessionInfo()
##R version 4.1.3 (2022-03-10)
##Platform: x86_64-conda-linux-gnu (64-bit)
##Running under: Ubuntu 18.04.6 LTS
##Matrix products: default
##BLAS/LAPACK: /media/dwheeler/spinner/Linux_space/miniconda3/envs/qiime2-2022.2/lib/libopenblasp-r0.3.20.so
##locale:
## [1] LC_CTYPE=en_AU.UTF-8       LC_NUMERIC=C              
## [3] LC_TIME=en_AU.UTF-8        LC_COLLATE=en_AU.UTF-8    
## [5] LC_MONETARY=en_AU.UTF-8    LC_MESSAGES=en_AU.UTF-8   
## [7] LC_PAPER=en_AU.UTF-8       LC_NAME=C                 
## [9] LC_ADDRESS=C               LC_TELEPHONE=C            
##[11] LC_MEASUREMENT=en_AU.UTF-8 LC_IDENTIFICATION=C       
##attached base packages:
##[1] stats     graphics  grDevices utils     datasets  methods   base     
##loaded via a namespace (and not attached):
##[1] compiler_4.1.3
