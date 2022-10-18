# STATS_CORRELATIONS
## Pairwise correlations with confidence intervals
Calculate Pearson correlations and confidence intervals.
The correlations are actually calculated by the built-in CORRELATIONS
procedure, the output from which is used in calculating the confidence
intervals.

---
Installation intructions
----
1. Open IBM SPSS Statistics
2. Navigate to Utilities -> Extension Bundles -> Download and Install Extension Bundles
3. Search for the name of the extension and click Ok. Your extension will be available.

---
Tutorial
----

### Installation Location

Analyze →

&nbsp;&nbsp;Correlate →

&nbsp;&nbsp;&nbsp;&nbsp;Bivariate with Confidence Intervals

### UI
<img width="659" alt="image" src="https://user-images.githubusercontent.com/19230800/196478833-a8854653-87f4-4b5b-8e17-380b262dc53f.png">

### Syntax
Example

> STATS CORRELATIONS VARIABLES=salary <br />
> /WITH VARIABLES=salbegin <br />
> /OPTIONS CONFLEVEL=95 METHOD=FISHER <br />
> /MISSING EXCLUDE=YES PAIRWISE=YES.

### Output

<img width="581" alt="image" src="https://user-images.githubusercontent.com/19230800/196479038-d626cf13-7a24-479e-944a-0808c12dd7e0.png">



---
License
----

- Apache 2.0
                              
Contributors
----

  - IBM SPSS JKP, JMB
