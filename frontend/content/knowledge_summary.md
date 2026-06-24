# Potassium dichromate equilibrium and color prediction

## 1. Chemical equilibrium

Many chemical reactions are reversible. Under fixed conditions, a reversible reaction reaches chemical equilibrium when the forward and reverse reaction rates become equal and the concentrations of each component remain macroscopically constant.

For a general reaction:

```text
mA + nB <=> pC + qD
```

the reaction quotient is:

```text
Q = c(C)^p c(D)^q / [c(A)^m c(B)^n]
```

At equilibrium, Q becomes a constant K. If an external factor changes the system, the equilibrium shifts in the direction that reduces the effect of that change. This is Le Chatelier's principle.

## 2. Color change of K2Cr2O7 solution

In potassium dichromate solution, the most important chromium(VI) equilibria are:

```text
Cr2O7^2- + H2O <=> 2HCrO4-
HCrO4- <=> H+ + CrO4^2-
```

Cr2O7^2- is orange, CrO4^2- is yellow, and HCrO4- is almost colorless in the visible range. Therefore, solution color reflects the relative distribution of these chromium species.

When hydroxide is added, [H+] decreases. The second equilibrium shifts toward CrO4^2-, and the first equilibrium also shifts toward HCrO4-. The visible result is that the solution becomes more yellow.

## 3. Activity and concentration

In ideal dilute solutions, concentration can be used directly in equilibrium calculations. In real electrolyte solutions, ion-ion and ion-solvent interactions cause deviations from ideal behavior, especially at higher ionic strength or for highly charged ions.

To describe this, concentration is corrected into activity:

```text
aB = gammaB * cB / c0
```

where aB is activity, gammaB is the activity coefficient, and c0 is the standard concentration, usually 1 mol/L. Strict thermodynamic equilibrium constants should use activities, but concentration-based constants are often acceptable for dilute solutions.

## 4. Reaction direction and Gibbs free energy

The direction of a reaction can be judged by comparing Q and K. It can also be judged thermodynamically by the molar Gibbs free energy change:

```text
Delta G = RT ln(Q / K)
```

Therefore:

```text
Q < K: forward reaction is favored
Q = K: equilibrium
Q > K: reverse reaction is favored
```

This connects the high-school description of equilibrium movement with thermodynamic driving force.

## 5. Temperature effect

Temperature changes affect equilibrium constants. The van't Hoff relation describes the relationship between temperature and K:

```text
d ln K / dT = Delta H / (R T^2)
```

For an endothermic reaction, increasing temperature increases K and favors the forward reaction. For an exothermic reaction, increasing temperature decreases K and disfavors the forward reaction.

For dichromate/chromate equilibria, if the relevant reactions are treated as endothermic, heating shifts the system toward more yellow CrO4^2-, while cooling makes the orange color deeper.

## 6. Color and chromium species concentration

Different chromium species have different electronic structures, so they absorb different wavelengths of light:

- Cr2O7^2- mainly absorbs blue-violet light, so the solution appears orange.
- CrO4^2- mainly absorbs blue-green light, so the solution appears yellow.
- HCrO4- absorbs mainly in the ultraviolet range, so it is nearly colorless to the eye.

The color depth is related to absorbing-species concentration. According to the Lambert-Beer law:

```text
A = epsilon * b * c
```

A is absorbance, epsilon is molar absorptivity, b is optical path length, and c is the absorbing species concentration. With multiple absorbing species, total absorbance is approximately the sum of the absorbance contributions from each species.

This is why the current model predicts the visible-ion system by combining image color features with pH and equilibrium calculations.

## 7. Why total Cr(VI) is not always the best direct target

The prepared total chromium(VI) concentration is not the direct cause of the measured color. The color is controlled by the equilibrium concentrations of Cr2O7^2-, HCrO4-, and CrO4^2-. Diluting or changing pH changes both total concentration and species distribution.

Therefore, the deployed route is:

```text
image + pH
-> illumination standardization
-> color feature extraction
-> direct prediction of HCrO4- and Cr2O7^2-
-> calculation of CrO4^2- from pH and Ka2
-> estimated total Cr(VI)
```

This route better matches the chemistry behind the visible color.
