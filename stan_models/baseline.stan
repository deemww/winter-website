
data {
  int<lower=1> N_gamma; int<lower=1> K_gamma; int<lower=1> M_gamma;
  matrix[N_gamma, K_gamma] X_gamma; vector[N_gamma] y_gamma; array[N_gamma] int m_gamma;
  int<lower=1> N_theta; int<lower=1> K_theta; int<lower=1> M_theta;
  matrix[N_theta, K_theta] X_theta; vector[N_theta] y_theta; array[N_theta] int m_theta;
  vector[N_theta] W_theta; int<lower=1> num_sites; matrix[num_sites, K_gamma] X_gamma_fit;
  array[num_sites] int m_gamma_fit; int<lower=1> C_theta_fit; matrix[C_theta_fit, K_theta] X_theta_fit;
  array[C_theta_fit] int m_theta_fit; int<lower=0> G_nnz_theta; vector[G_nnz_theta] G_w_theta;
  array[G_nnz_theta] int G_v_theta; array[num_sites + 1] int G_u_theta; real pa_2017;
}
transformed data {
  vector[N_theta] y_theta_w = W_theta .* y_theta;
  matrix[N_theta, K_theta] X_theta_w;
  for (n in 1 : N_theta) X_theta_w[n] = W_theta[n] * X_theta[n];
}
parameters {
  vector[K_gamma] beta_gamma; vector[M_gamma] nu_gamma; real log_precision_u_gamma; real log_precision_v_gamma;
  vector[K_theta] beta_theta; vector[M_theta] nu_theta; real log_precision_u_theta; real log_precision_v_theta;
}
transformed parameters {
  vector[N_theta] nu_theta_w = W_theta .* nu_theta[m_theta];
  vector[C_theta_fit] nu_theta_fit = nu_theta[m_theta_fit];
  vector[N_gamma] nu_gamma_sort = nu_gamma[m_gamma];
  vector[num_sites] nu_gamma_fit = nu_gamma[m_gamma_fit];
  real sigma_u_gamma = exp(-0.5 * log_precision_u_gamma);
  real sigma_v_gamma = exp(-0.5 * log_precision_v_gamma);
  real sigma_u_theta = exp(-0.5 * log_precision_u_theta);
  real sigma_v_theta = exp(-0.5 * log_precision_v_theta);
  vector<lower=0>[num_sites] gamma = exp(X_gamma_fit * beta_gamma + nu_gamma_fit);
  vector[C_theta_fit] exp_log_theta = exp(X_theta_fit * beta_theta + nu_theta_fit);
  vector<lower=0>[num_sites] theta = csr_matrix_times_vector(num_sites, C_theta_fit, G_w_theta, G_v_theta, G_u_theta, exp_log_theta) / pa_2017;
}
model {
  nu_gamma ~ normal(0, sigma_v_gamma);
  nu_theta ~ normal(0, sigma_v_theta);
  y_gamma ~ normal(X_gamma * beta_gamma + nu_gamma_sort, sigma_u_gamma);
  y_theta_w ~ normal(X_theta_w * beta_theta + nu_theta_w, sigma_u_theta);
}
