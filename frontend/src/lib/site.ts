/**
 * Operator details shown in the footer. The Figma values are fictional samples, so the
 * real ones come from build-time settings (non-secret) and stay as placeholders until set.
 */
export const siteOperator = {
  name: process.env.SITE_OPERATOR_NAME || null,
  representative: process.env.SITE_OPERATOR_REPRESENTATIVE || null,
  email: process.env.SITE_OPERATOR_EMAIL || null,
  address: process.env.SITE_OPERATOR_ADDRESS || null,
};
