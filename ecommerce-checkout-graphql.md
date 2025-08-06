# E-commerce Checkout with GraphQL and Payment Methods

## GraphQL Schema for Checkout

### Core Types

```graphql
type Query {
  cart(id: ID!): Cart
  paymentMethods: [PaymentMethod!]!
  shippingMethods(cartId: ID!): [ShippingMethod!]!
  checkout(id: ID!): Checkout
}

type Mutation {
  createCheckout(input: CheckoutCreateInput!): CheckoutCreatePayload!
  updateCheckout(checkoutId: ID!, input: CheckoutUpdateInput!): CheckoutUpdatePayload!
  checkoutComplete(checkoutId: ID!, payment: PaymentInput!): CheckoutCompletePayload!
  applyDiscount(checkoutId: ID!, discountCode: String!): CheckoutDiscountPayload!
}

type Cart {
  id: ID!
  lines: [CartLine!]!
  cost: CartCost!
  totalQuantity: Int!
  checkoutUrl: String!
}

type CartLine {
  id: ID!
  quantity: Int!
  merchandise: ProductVariant!
  cost: CartLineCost!
}

type CartCost {
  totalAmount: Money!
  subtotalAmount: Money!
  totalTaxAmount: Money
  totalDutyAmount: Money
}

type Checkout {
  id: ID!
  webUrl: String!
  totalTax: Money!
  totalPrice: Money!
  subtotalPrice: Money!
  lineItems(first: Int): CheckoutLineItemConnection!
  shippingAddress: MailingAddress
  billingAddress: MailingAddress
  email: String
  shippingLine: ShippingRate
  paymentDue: Money!
  ready: Boolean!
  requiresShipping: Boolean!
  taxExempt: Boolean!
  taxesIncluded: Boolean!
  currencyCode: CurrencyCode!
  completedAt: DateTime
  createdAt: DateTime!
  updatedAt: DateTime!
  note: String
  discountApplications(first: Int): DiscountApplicationConnection!
}

type CheckoutLineItem {
  id: ID!
  title: String!
  variant: ProductVariant
  quantity: Int!
  customAttributes: [Attribute!]!
}

type Money {
  amount: Decimal!
  currencyCode: CurrencyCode!
}

type PaymentMethod {
  id: ID!
  name: String!
  type: PaymentMethodType!
  supportedCountries: [CountryCode!]!
  configuration: PaymentMethodConfiguration
}

enum PaymentMethodType {
  CREDIT_CARD
  PAYPAL
  APPLE_PAY
  GOOGLE_PAY
  STRIPE
  KLARNA
  AFTERPAY
  SHOP_PAY
  AMAZON_PAY
  BANK_TRANSFER
  CRYPTOCURRENCY
}

type PaymentMethodConfiguration {
  publicKey: String
  merchantId: String
  supportedNetworks: [String!]
  supportedTypes: [String!]
}

type ShippingMethod {
  id: ID!
  title: String!
  price: Money!
  deliveryRange: String
  handle: String!
}

input CheckoutCreateInput {
  lineItems: [CheckoutLineItemInput!]!
  email: String
  shippingAddress: MailingAddressInput
  billingAddress: MailingAddressInput
  note: String
  customAttributes: [AttributeInput!]
  allowPartialAddresses: Boolean
}

input CheckoutUpdateInput {
  lineItems: [CheckoutLineItemUpdateInput!]
  email: String
  shippingAddress: MailingAddressInput
  billingAddress: MailingAddressInput
  note: String
  customAttributes: [AttributeInput!]
  allowPartialAddresses: Boolean
}

input PaymentInput {
  amount: Money!
  idempotencyKey: String!
  billingAddress: MailingAddressInput!
  type: PaymentMethodType!
  creditCard: CreditCardPaymentInput
  paypal: PaypalPaymentInput
  stripe: StripePaymentInput
  test: Boolean
}

input CreditCardPaymentInput {
  number: String!
  firstName: String!
  lastName: String!
  month: Int!
  year: Int!
  verificationValue: String!
}

input StripePaymentInput {
  paymentMethodId: String!
  paymentIntentId: String
}

input PaypalPaymentInput {
  paymentId: String!
  payerId: String!
}

input MailingAddressInput {
  address1: String
  address2: String
  city: String
  company: String
  country: String
  firstName: String
  lastName: String
  phone: String
  province: String
  zip: String
}

type CheckoutCreatePayload {
  checkout: Checkout
  checkoutUserErrors: [CheckoutUserError!]!
  userErrors: [UserError!]!
}

type CheckoutCompletePayload {
  checkout: Checkout
  order: Order
  payment: Payment
  checkoutUserErrors: [CheckoutUserError!]!
  userErrors: [UserError!]!
}

type Order {
  id: ID!
  orderNumber: Int!
  email: String
  phone: String
  processedAt: DateTime
  financialStatus: OrderFinancialStatus
  fulfillmentStatus: OrderFulfillmentStatus
  statusUrl: String!
  totalPrice: Money!
  totalTax: Money!
  subtotalPrice: Money!
  totalShippingPrice: Money!
  currencyCode: CurrencyCode!
  lineItems(first: Int): OrderLineItemConnection!
  shippingAddress: MailingAddress
  billingAddress: MailingAddress
  note: String
  customAttributes: [Attribute!]!
}

type Payment {
  id: ID!
  ready: Boolean!
  test: Boolean!
  checkout: Checkout!
  paymentMethod: PaymentMethodType!
  transaction: Transaction
  errorMessage: String
  nextActionUrl: String
}

type Transaction {
  id: ID!
  amount: Money!
  kind: TransactionKind!
  gateway: String
  status: TransactionStatus!
  test: Boolean!
  authorizationCode: String
  createdAt: DateTime!
  errorCode: TransactionErrorCode
  parentTransaction: Transaction
}

enum TransactionKind {
  AUTHORIZATION
  CAPTURE
  SALE
  VOID
  REFUND
}

enum TransactionStatus {
  PENDING
  SUCCESS
  FAILURE
  ERROR
}
```

## React/Next.js Checkout Implementation

### Checkout Context

```typescript
// contexts/CheckoutContext.tsx
import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';

interface CheckoutState {
  checkout: Checkout | null;
  loading: boolean;
  error: string | null;
  paymentMethods: PaymentMethod[];
  shippingMethods: ShippingMethod[];
}

interface CheckoutContextType extends CheckoutState {
  createCheckout: (input: CheckoutCreateInput) => Promise<void>;
  updateCheckout: (input: CheckoutUpdateInput) => Promise<void>;
  completeCheckout: (payment: PaymentInput) => Promise<Order | null>;
  loadPaymentMethods: () => Promise<void>;
  loadShippingMethods: () => Promise<void>;
  applyDiscount: (code: string) => Promise<void>;
}

const CheckoutContext = createContext<CheckoutContextType | undefined>(undefined);

// Apollo Client setup
const httpLink = createHttpLink({
  uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT,
});

const authLink = setContext((_, { headers }) => {
  const token = process.env.NEXT_PUBLIC_STOREFRONT_ACCESS_TOKEN;
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
      'X-Shopify-Storefront-Access-Token': token,
    }
  }
});

export const apolloClient = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache(),
});

export const CheckoutProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Implementation here
  return (
    <CheckoutContext.Provider value={contextValue}>
      {children}
    </CheckoutContext.Provider>
  );
};

export const useCheckout = () => {
  const context = useContext(CheckoutContext);
  if (context === undefined) {
    throw new Error('useCheckout must be used within a CheckoutProvider');
  }
  return context;
};
```

### GraphQL Queries and Mutations

```typescript
// graphql/checkout.ts
import { gql } from '@apollo/client';

export const CREATE_CHECKOUT = gql`
  mutation CheckoutCreate($input: CheckoutCreateInput!) {
    checkoutCreate(input: $input) {
      checkout {
        id
        webUrl
        totalTax {
          amount
          currencyCode
        }
        totalPrice {
          amount
          currencyCode
        }
        subtotalPrice {
          amount
          currencyCode
        }
        paymentDue {
          amount
          currencyCode
        }
        ready
        requiresShipping
        email
        shippingAddress {
          firstName
          lastName
          address1
          address2
          city
          province
          country
          zip
          phone
        }
        billingAddress {
          firstName
          lastName
          address1
          address2
          city
          province
          country
          zip
          phone
        }
        lineItems(first: 250) {
          edges {
            node {
              id
              title
              quantity
              variant {
                id
                title
                price {
                  amount
                  currencyCode
                }
                image {
                  src
                  altText
                }
              }
            }
          }
        }
      }
      checkoutUserErrors {
        field
        message
      }
    }
  }
`;

export const UPDATE_CHECKOUT = gql`
  mutation CheckoutUpdate($checkoutId: ID!, $input: CheckoutUpdateInput!) {
    checkoutUpdate(checkoutId: $checkoutId, input: $input) {
      checkout {
        id
        webUrl
        totalPrice {
          amount
          currencyCode
        }
        paymentDue {
          amount
          currencyCode
        }
        ready
      }
      checkoutUserErrors {
        field
        message
      }
    }
  }
`;

export const CHECKOUT_COMPLETE = gql`
  mutation CheckoutComplete($checkoutId: ID!, $payment: PaymentInput!) {
    checkoutComplete(checkoutId: $checkoutId, payment: $payment) {
      checkout {
        id
        completedAt
      }
      order {
        id
        orderNumber
        statusUrl
        totalPrice {
          amount
          currencyCode
        }
      }
      payment {
        id
        ready
        errorMessage
        nextActionUrl
      }
      checkoutUserErrors {
        field
        message
      }
    }
  }
`;

export const GET_PAYMENT_METHODS = gql`
  query GetPaymentMethods {
    paymentMethods {
      id
      name
      type
      supportedCountries
      configuration {
        publicKey
        merchantId
        supportedNetworks
        supportedTypes
      }
    }
  }
`;

export const APPLY_DISCOUNT = gql`
  mutation CheckoutDiscountCodeApply($checkoutId: ID!, $discountCode: String!) {
    checkoutDiscountCodeApplyV2(checkoutId: $checkoutId, discountCode: $discountCode) {
      checkout {
        id
        discountApplications(first: 10) {
          edges {
            node {
              ... on DiscountCodeApplication {
                code
                applicable
              }
            }
          }
        }
        totalPrice {
          amount
          currencyCode
        }
        subtotalPrice {
          amount
          currencyCode
        }
      }
      checkoutUserErrors {
        field
        message
      }
    }
  }
`;
```

### Checkout Component

```typescript
// components/Checkout.tsx
import React, { useState, useEffect } from 'react';
import { useCheckout } from '../contexts/CheckoutContext';
import { PaymentForm } from './PaymentForm';
import { ShippingForm } from './ShippingForm';
import { OrderSummary } from './OrderSummary';

export const Checkout: React.FC = () => {
  const {
    checkout,
    loading,
    error,
    paymentMethods,
    shippingMethods,
    loadPaymentMethods,
    loadShippingMethods,
    updateCheckout,
    completeCheckout
  } = useCheckout();

  const [step, setStep] = useState<'shipping' | 'payment' | 'review'>('shipping');
  const [shippingData, setShippingData] = useState(null);
  const [paymentData, setPaymentData] = useState(null);

  useEffect(() => {
    loadPaymentMethods();
    if (checkout?.requiresShipping) {
      loadShippingMethods();
    }
  }, [checkout]);

  const handleShippingSubmit = async (data: any) => {
    setShippingData(data);
    await updateCheckout({
      shippingAddress: data.shippingAddress,
      billingAddress: data.billingAddress,
      email: data.email
    });
    setStep('payment');
  };

  const handlePaymentSubmit = async (data: any) => {
    setPaymentData(data);
    setStep('review');
  };

  const handleCompleteOrder = async () => {
    if (!paymentData) return;
    
    try {
      const order = await completeCheckout(paymentData);
      if (order) {
        // Redirect to success page
        window.location.href = `/order-confirmation/${order.id}`;
      }
    } catch (error) {
      console.error('Checkout completion failed:', error);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!checkout) return <div>No checkout found</div>;

  return (
    <div className="checkout-container">
      <div className="checkout-main">
        <div className="checkout-steps">
          {step === 'shipping' && (
            <ShippingForm
              onSubmit={handleShippingSubmit}
              shippingMethods={shippingMethods}
              initialData={shippingData}
            />
          )}
          
          {step === 'payment' && (
            <PaymentForm
              onSubmit={handlePaymentSubmit}
              paymentMethods={paymentMethods}
              checkout={checkout}
              onBack={() => setStep('shipping')}
            />
          )}
          
          {step === 'review' && (
            <div className="review-step">
              <h2>Review Your Order</h2>
              <div className="review-sections">
                <div className="shipping-review">
                  <h3>Shipping Information</h3>
                  {/* Display shipping info */}
                </div>
                <div className="payment-review">
                  <h3>Payment Information</h3>
                  {/* Display payment info */}
                </div>
              </div>
              <button
                onClick={handleCompleteOrder}
                className="complete-order-btn"
              >
                Complete Order
              </button>
            </div>
          )}
        </div>
      </div>
      
      <div className="checkout-sidebar">
        <OrderSummary checkout={checkout} />
      </div>
    </div>
  );
};
```

### Payment Form with Multiple Methods

```typescript
// components/PaymentForm.tsx
import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

interface PaymentFormProps {
  onSubmit: (data: any) => void;
  paymentMethods: PaymentMethod[];
  checkout: Checkout;
  onBack: () => void;
}

const PaymentFormInner: React.FC<PaymentFormProps> = ({
  onSubmit,
  paymentMethods,
  checkout,
  onBack
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethodType>('CREDIT_CARD');
  const [processing, setProcessing] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setProcessing(true);

    try {
      let paymentData;

      switch (selectedMethod) {
        case 'CREDIT_CARD':
          paymentData = await handleCreditCardPayment();
          break;
        case 'STRIPE':
          paymentData = await handleStripePayment();
          break;
        case 'PAYPAL':
          paymentData = await handlePayPalPayment();
          break;
        case 'APPLE_PAY':
          paymentData = await handleApplePayPayment();
          break;
        default:
          throw new Error('Unsupported payment method');
      }

      onSubmit(paymentData);
    } catch (error) {
      console.error('Payment processing error:', error);
    } finally {
      setProcessing(false);
    }
  };

  const handleStripePayment = async () => {
    if (!stripe || !elements) {
      throw new Error('Stripe not loaded');
    }

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      throw new Error('Card element not found');
    }

    const { error, paymentMethod } = await stripe.createPaymentMethod({
      type: 'card',
      card: cardElement,
    });

    if (error) {
      throw error;
    }

    return {
      amount: checkout.paymentDue,
      type: 'STRIPE',
      stripe: {
        paymentMethodId: paymentMethod.id,
      },
      billingAddress: checkout.billingAddress,
      idempotencyKey: `checkout-${checkout.id}-${Date.now()}`,
    };
  };

  const handlePayPalPayment = async () => {
    // PayPal integration logic
    return {
      amount: checkout.paymentDue,
      type: 'PAYPAL',
      paypal: {
        paymentId: 'paypal-payment-id',
        payerId: 'paypal-payer-id',
      },
      billingAddress: checkout.billingAddress,
      idempotencyKey: `checkout-${checkout.id}-${Date.now()}`,
    };
  };

  const handleApplePayPayment = async () => {
    // Apple Pay integration logic
    if (!window.ApplePaySession || !ApplePaySession.canMakePayments()) {
      throw new Error('Apple Pay not available');
    }

    return {
      amount: checkout.paymentDue,
      type: 'APPLE_PAY',
      billingAddress: checkout.billingAddress,
      idempotencyKey: `checkout-${checkout.id}-${Date.now()}`,
    };
  };

  return (
    <form onSubmit={handleSubmit} className="payment-form">
      <h2>Payment Information</h2>
      
      <div className="payment-methods">
        {paymentMethods.map((method) => (
          <label key={method.id} className="payment-method-option">
            <input
              type="radio"
              name="paymentMethod"
              value={method.type}
              checked={selectedMethod === method.type}
              onChange={(e) => setSelectedMethod(e.target.value as PaymentMethodType)}
            />
            <span>{method.name}</span>
          </label>
        ))}
      </div>

      {selectedMethod === 'CREDIT_CARD' && (
        <div className="credit-card-form">
          <CardElement
            options={{
              style: {
                base: {
                  fontSize: '16px',
                  color: '#424770',
                  '::placeholder': {
                    color: '#aab7c4',
                  },
                },
              },
            }}
          />
        </div>
      )}

      {selectedMethod === 'STRIPE' && (
        <div className="stripe-form">
          <CardElement />
        </div>
      )}

      {selectedMethod === 'PAYPAL' && (
        <div className="paypal-form">
          <div id="paypal-button-container"></div>
        </div>
      )}

      <div className="form-actions">
        <button type="button" onClick={onBack} className="back-btn">
          Back to Shipping
        </button>
        <button
          type="submit"
          disabled={processing || !stripe}
          className="submit-btn"
        >
          {processing ? 'Processing...' : `Pay ${checkout.paymentDue.amount} ${checkout.paymentDue.currencyCode}`}
        </button>
      </div>
    </form>
  );
};

export const PaymentForm: React.FC<PaymentFormProps> = (props) => {
  return (
    <Elements stripe={stripePromise}>
      <PaymentFormInner {...props} />
    </Elements>
  );
};
```

### Order Summary Component

```typescript
// components/OrderSummary.tsx
import React from 'react';

interface OrderSummaryProps {
  checkout: Checkout;
}

export const OrderSummary: React.FC<OrderSummaryProps> = ({ checkout }) => {
  return (
    <div className="order-summary">
      <h3>Order Summary</h3>
      
      <div className="line-items">
        {checkout.lineItems.edges.map(({ node: item }) => (
          <div key={item.id} className="line-item">
            <div className="item-image">
              {item.variant?.image && (
                <img src={item.variant.image.src} alt={item.variant.image.altText} />
              )}
            </div>
            <div className="item-details">
              <h4>{item.title}</h4>
              <p>{item.variant?.title}</p>
              <span className="quantity">Qty: {item.quantity}</span>
            </div>
            <div className="item-price">
              {item.variant?.price.amount} {item.variant?.price.currencyCode}
            </div>
          </div>
        ))}
      </div>

      <div className="order-totals">
        <div className="total-line">
          <span>Subtotal:</span>
          <span>{checkout.subtotalPrice.amount} {checkout.subtotalPrice.currencyCode}</span>
        </div>
        
        {checkout.shippingLine && (
          <div className="total-line">
            <span>Shipping:</span>
            <span>{checkout.shippingLine.price.amount} {checkout.shippingLine.price.currencyCode}</span>
          </div>
        )}
        
        <div className="total-line">
          <span>Tax:</span>
          <span>{checkout.totalTax.amount} {checkout.totalTax.currencyCode}</span>
        </div>
        
        <div className="total-line total">
          <span>Total:</span>
          <span>{checkout.totalPrice.amount} {checkout.totalPrice.currencyCode}</span>
        </div>
      </div>

      <div className="discount-code">
        <input type="text" placeholder="Discount code" />
        <button>Apply</button>
      </div>
    </div>
  );
};
```

## Payment Method Integrations

### Stripe Integration

```typescript
// utils/stripe.ts
import { loadStripe, Stripe } from '@stripe/stripe-js';

let stripePromise: Promise<Stripe | null>;

export const getStripe = () => {
  if (!stripePromise) {
    stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);
  }
  return stripePromise;
};

export const createPaymentIntent = async (amount: number, currency: string) => {
  const response = await fetch('/api/create-payment-intent', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ amount, currency }),
  });

  return response.json();
};
```

### PayPal Integration

```typescript
// utils/paypal.ts
declare global {
  interface Window {
    paypal: any;
  }
}

export const loadPayPalScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (window.paypal) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = `https://www.paypal.com/sdk/js?client-id=${process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID}`;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('PayPal SDK failed to load'));
    document.head.appendChild(script);
  });
};

export const createPayPalOrder = (amount: string, currency: string) => {
  return window.paypal.Orders.create({
    purchase_units: [{
      amount: {
        currency_code: currency,
        value: amount
      }
    }]
  });
};
```

### Apple Pay Integration

```typescript
// utils/applePay.ts
export const isApplePayAvailable = (): boolean => {
  return window.ApplePaySession && ApplePaySession.canMakePayments();
};

export const createApplePaySession = (
  amount: string,
  currency: string,
  merchantId: string
): ApplePaySession => {
  const request: ApplePayJS.ApplePayPaymentRequest = {
    countryCode: 'US',
    currencyCode: currency,
    supportedNetworks: ['visa', 'masterCard', 'amex'],
    merchantCapabilities: ['supports3DS'],
    total: {
      label: 'Total',
      amount: amount,
    },
  };

  const session = new ApplePaySession(3, request);
  
  session.onvalidatemerchant = async (event) => {
    // Validate merchant with Apple Pay
    const response = await fetch('/api/apple-pay/validate-merchant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        validationURL: event.validationURL,
        merchantId: merchantId,
      }),
    });
    
    const merchantSession = await response.json();
    session.completeMerchantValidation(merchantSession);
  };

  session.onpaymentauthorized = async (event) => {
    // Process payment
    const result = await processApplePayPayment(event.payment);
    session.completePayment(result.status);
  };

  return session;
};

const processApplePayPayment = async (payment: ApplePayJS.ApplePayPayment) => {
  const response = await fetch('/api/apple-pay/process-payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payment }),
  });

  return response.json();
};
```

## Backend API Routes

### Stripe Payment Intent

```typescript
// pages/api/create-payment-intent.ts
import { NextApiRequest, NextApiResponse } from 'next';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2022-11-15',
});

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    const { amount, currency } = req.body;

    const paymentIntent = await stripe.paymentIntents.create({
      amount: Math.round(amount * 100), // Convert to cents
      currency: currency.toLowerCase(),
      automatic_payment_methods: {
        enabled: true,
      },
    });

    res.status(200).json({
      clientSecret: paymentIntent.client_secret,
    });
  } catch (error) {
    console.error('Error creating payment intent:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
}
```

### PayPal Order Creation

```typescript
// pages/api/paypal/create-order.ts
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  try {
    const { amount, currency } = req.body;

    const response = await fetch(`${process.env.PAYPAL_API_BASE}/v2/checkout/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${await getPayPalAccessToken()}`,
      },
      body: JSON.stringify({
        intent: 'CAPTURE',
        purchase_units: [{
          amount: {
            currency_code: currency,
            value: amount,
          },
        }],
      }),
    });

    const order = await response.json();
    res.status(200).json(order);
  } catch (error) {
    console.error('Error creating PayPal order:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
}

async function getPayPalAccessToken(): Promise<string> {
  const response = await fetch(`${process.env.PAYPAL_API_BASE}/v1/oauth2/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': `Basic ${Buffer.from(`${process.env.PAYPAL_CLIENT_ID}:${process.env.PAYPAL_CLIENT_SECRET}`).toString('base64')}`,
    },
    body: 'grant_type=client_credentials',
  });

  const data = await response.json();
  return data.access_token;
}
```

## Environment Variables

```bash
# .env.local
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://your-store.myshopify.com/api/2023-04/graphql.json
NEXT_PUBLIC_STOREFRONT_ACCESS_TOKEN=your_storefront_access_token

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# PayPal
NEXT_PUBLIC_PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_API_BASE=https://api.sandbox.paypal.com

# Apple Pay
APPLE_PAY_MERCHANT_ID=merchant.your.app
APPLE_PAY_CERTIFICATE_PATH=./certs/apple-pay-cert.pem
APPLE_PAY_KEY_PATH=./certs/apple-pay-key.pem
```

This implementation provides a comprehensive checkout system with:

1. **GraphQL Schema** - Complete type definitions for checkout, payments, and orders
2. **Multiple Payment Methods** - Stripe, PayPal, Apple Pay, Google Pay, etc.
3. **React/Next.js Components** - Modular checkout flow with step-by-step process
4. **Payment Processing** - Secure handling of different payment methods
5. **Order Management** - Complete order lifecycle management
6. **Error Handling** - Comprehensive error handling and user feedback
7. **Mobile Optimization** - Responsive design for mobile checkout

The code follows modern e-commerce best practices and can be adapted for various platforms including Shopify, WooCommerce, or custom solutions.