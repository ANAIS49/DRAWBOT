/**
 * @file    pid.h
 * @brief   Régulateur PID générique réutilisable.
 *
 * Caractéristiques :
 *   - Anti-windup par clamp de l'intégrale
 *   - Saturation de la sortie
 *   - Dérivée calculée sur la mesure (et non l'erreur) pour éviter
 *     les pics au changement de consigne ("derivative kick")
 *   - Filtre passe-bas optionnel sur le terme dérivé
 */
#pragma once

class PID {
public:
    /**
     * @param kp gain proportionnel
     * @param ki gain intégral
     * @param kd gain dérivé
     */
    PID(float kp = 0.0f, float ki = 0.0f, float kd = 0.0f);

    void setGains(float kp, float ki, float kd);
    void getGains(float &kp, float &ki, float &kd) const;

    /// Saturation de la sortie (par défaut : pas de limite).
    void setOutputLimits(float minOut, float maxOut);

    /// Anti-windup : limite la valeur du terme intégral.
    void setIntegralLimits(float minI, float maxI);

    /// Coefficient α du filtre dérivé (0 = pas de filtrage, 0.1 par défaut).
    void setDerivativeFilter(float alpha);

    void  setSetpoint(float sp);
    float getSetpoint() const { return _setpoint; }

    /**
     * @brief Calcule la sortie du PID.
     * @param measurement valeur mesurée
     * @param dt          intervalle depuis le dernier appel, en secondes
     * @return commande (déjà saturée)
     */
    float compute(float measurement, float dt);

    /// Réinitialise l'historique interne (intégrale, dérivée).
    void reset();

private:
    float _kp, _ki, _kd;
    float _setpoint;
    float _integral;
    float _last_measurement;
    float _last_deriv_filtered;
    float _out_min, _out_max;
    float _i_min,   _i_max;
    float _d_alpha;
    bool  _has_last;   ///< false au premier appel ou après reset()
};
