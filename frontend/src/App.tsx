import {
  BarChart3,
  Boxes,
  LayoutDashboard,
  LogOut,
  Minus,
  Package,
  Plus,
  Printer,
  Receipt,
  Search,
  Settings,
  ShoppingCart,
  Trash2,
  Truck,
  Users,
  WalletCards,
} from "lucide-react";

import {
  FormEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";


const API = (
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api"
).replace(/\/$/, "");


type User = {
  id: string;
  shop_id: string;
  username: string;
  full_name: string;
  email?: string | null;
  role: string;
  status: string;
  is_super_admin: boolean;
};


type Product = {
  id: string;
  name: string;
  sku?: string | null;
  unit: string;
  purchase_price: number;
  selling_price: number;
  wholesale_price?: number;
  minimum_price?: number;
  stock_quantity: number;
  minimum_stock: number;
  maximum_stock?: number;
  active: boolean;
};


type CartItem = Product & {
  quantity: number;
  discount: number;
};


type Dashboard = {
  sales_count: number;
  sales_total: number;
  discount_total: number;
  credit_total: number;
  expense_total: number;
  active_products: number;
  low_stock_products: number;
};


function money(
  value: number | string | null | undefined,
) {
  return `PKR ${Number(value || 0).toLocaleString(
    "en-PK",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    },
  )}`;
}


async function api(
  path: string,
  options: RequestInit = {},
) {
  const token =
    localStorage.getItem("pos_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers || {}) as Record<
      string,
      string
    >),
  };

  if (token) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  const response = await fetch(
    `${API}${path}`,
    {
      ...options,
      headers,
    },
  );

  const contentType =
    response.headers.get("content-type") ||
    "";

  const body =
    contentType.includes(
      "application/json",
    )
      ? await response.json()
      : await response.text();

  if (!response.ok) {
    const message =
      typeof body === "object" && body
        ? body.detail ||
          body.message ||
          `Request failed (${response.status})`
        : body;

    throw new Error(
      message ||
        `Request failed (${response.status})`,
    );
  }

  return body;
}


function Login({
  onLogin,
}: {
  onLogin: (user: User) => void;
}) {
  const [username, setUsername] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  async function submit(
    event: FormEvent,
  ) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const result =
        await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            username,
            password,
          }),
        });

      localStorage.setItem(
        "pos_token",
        result.access_token,
      );

      localStorage.setItem(
        "pos_user",
        JSON.stringify(result.user),
      );

      onLogin(result.user);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Login failed.",
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="login-page">
      <form
        className="login-card"
        onSubmit={submit}
      >
        <div className="brand-mark">
          POS
        </div>

        <div className="login-title">
          General Store POS
        </div>

        <div className="login-description">
          Professional point-of-sale
          management for products, stock,
          sales, customers, suppliers and
          daily cash operations.
        </div>

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        <div className="form-group">
          <label className="label">
            Username
          </label>

          <input
            className="input"
            autoFocus
            autoComplete="username"
            value={username}
            onChange={(event) =>
              setUsername(
                event.target.value,
              )
            }
            placeholder="Enter username"
          />
        </div>

        <div className="form-group">
          <label className="label">
            Password
          </label>

          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) =>
              setPassword(
                event.target.value,
              )
            }
            placeholder="Enter password"
          />
        </div>

        <button
          className="btn btn-primary"
          disabled={
            loading ||
            !username ||
            !password
          }
          style={{
            width: "100%",
            padding: 12,
          }}
        >
          {loading
            ? "Signing in..."
            : "Sign in"}
        </button>
      </form>
    </div>
  );
}


function App() {
  const [user, setUser] =
    useState<User | null>(() => {
      try {
        const stored =
          localStorage.getItem(
            "pos_user",
          );

        return stored
          ? JSON.parse(stored)
          : null;
      } catch {
        return null;
      }
    });


  if (!user) {
    return (
      <Login
        onLogin={setUser}
      />
    );
  }


  return (
    <POSApplication
      user={user}
      onLogout={() => {
        localStorage.removeItem(
          "pos_token",
        );

        localStorage.removeItem(
          "pos_user",
        );

        setUser(null);
      }}
    />
  );
}


function POSApplication({
  user,
  onLogout,
}: {
  user: User;
  onLogout: () => void;
}) {
  const [page, setPage] =
    useState("dashboard");

  const [toast, setToast] =
    useState("");

  const [dashboard, setDashboard] =
    useState<Dashboard | null>(null);

  const [products, setProducts] =
    useState<Product[]>([]);

  const [cart, setCart] =
    useState<CartItem[]>([]);

  const [search, setSearch] =
    useState("");

  const [barcode, setBarcode] =
    useState("");

  const [billDiscount, setBillDiscount] =
    useState(0);

  const [paymentMethod, setPaymentMethod] =
    useState("cash");

  const [cashReceived, setCashReceived] =
    useState(0);

  const barcodeRef =
    useRef<HTMLInputElement>(null);


  function notify(
    message: string,
  ) {
    setToast(message);

    window.setTimeout(
      () => setToast(""),
      3000,
    );
  }


  async function loadDashboard() {
    try {
      const result =
        await api(
          "/reports/dashboard",
        );

      setDashboard(result);
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load dashboard.",
      );
    }
  }


  async function loadProducts() {
    try {
      const result =
        await api(
          "/products?page_size=200",
        );

      setProducts(
        Array.isArray(result)
          ? result
          : result.items || [],
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load products.",
      );
    }
  }


  useEffect(() => {
    loadDashboard();
    loadProducts();
  }, []);


  useEffect(() => {
    if (page === "pos") {
      window.setTimeout(
        () =>
          barcodeRef.current?.focus(),
        100,
      );
    }
  }, [page]);


  const filteredProducts =
    useMemo(() => {
      const term =
        search.trim().toLowerCase();

      if (!term) {
        return products.slice(
          0,
          100,
        );
      }

      return products
        .filter((product) =>
          [
            product.name,
            product.sku,
          ]
            .filter(Boolean)
            .some((value) =>
              String(value)
                .toLowerCase()
                .includes(term),
            ),
        )
        .slice(0, 100);
    }, [products, search]);


  const subtotal =
    cart.reduce(
      (sum, item) =>
        sum +
        item.quantity *
          Number(
            item.selling_price,
          ) -
        Number(
          item.discount || 0,
        ),
      0,
    );


  const total = Math.max(
    0,
    subtotal - billDiscount,
  );


  const change = Math.max(
    0,
    cashReceived - total,
  );


  function addToCart(
    product: Product,
  ) {
    if (
      !product.active ||
      Number(
        product.stock_quantity,
      ) <= 0
    ) {
      notify(
        "This product is out of stock.",
      );

      return;
    }

    setCart((current) => {
      const existing =
        current.find(
          (item) =>
            item.id ===
            product.id,
        );

      if (existing) {
        return current.map(
          (item) =>
            item.id === product.id
              ? {
                  ...item,
                  quantity:
                    Math.min(
                      Number(
                        product.stock_quantity,
                      ),
                      item.quantity +
                        1,
                    ),
                }
              : item,
        );
      }

      return [
        ...current,
        {
          ...product,
          quantity: 1,
          discount: 0,
        },
      ];
    });
  }


  function updateQuantity(
    id: string,
    amount: number,
  ) {
    setCart((current) =>
      current
        .map((item) => {
          if (item.id !== id) {
            return item;
          }

          const quantity =
            Math.max(
              0,
              Math.min(
                Number(
                  item.stock_quantity,
                ),
                amount,
              ),
            );

          return {
            ...item,
            quantity,
          };
        })
        .filter(
          (item) =>
            item.quantity > 0,
        ),
    );
  }


  async function scanBarcode(
    event?: FormEvent,
  ) {
    event?.preventDefault();

    const value =
      barcode.trim();

    if (!value) {
      return;
    }

    try {
      /*
       * IMPORTANT:
       * The backend uses the product
       * barcode lookup endpoint below.
       */
      const lookup =
        await api(
          `/products/lookup/code/${encodeURIComponent(
            value,
          )}`,
        );

      const productId =
        lookup.product_id ||
        lookup.id ||
        lookup.product?.id;

      if (!productId) {
        throw new Error(
          "Product was not found.",
        );
      }

      const product =
        await api(
          `/products/${productId}`,
        );

      addToCart(product);

      setBarcode("");

      window.setTimeout(
        () =>
          barcodeRef.current?.focus(),
        50,
      );
    } catch {
      notify(
        `Barcode "${value}" was not found.`,
      );
    }
  }


  async function completeSale() {
    if (!cart.length) {
      notify("Cart is empty.");
      return;
    }

    if (
      paymentMethod === "cash" &&
      cashReceived < total
    ) {
      notify(
        "Cash received is less than the total.",
      );

      return;
    }

    try {
      const result =
        await api("/sales", {
          method: "POST",
          body: JSON.stringify({
            items: cart.map(
              (item) => ({
                product_id:
                  item.id,
                quantity:
                  item.quantity,
                unit_price:
                  item.selling_price,
                discount:
                  item.discount,
              }),
            ),
            discount:
              billDiscount,
            payments: [
              {
                method:
                  paymentMethod,
                amount: total,
                received_amount:
                  paymentMethod ===
                  "cash"
                    ? cashReceived
                    : total,
              },
            ],
          }),
        });

      setCart([]);
      setBillDiscount(0);
      setCashReceived(0);

      await loadDashboard();
      await loadProducts();

      notify(
        `Sale completed: ${
          result.receipt_number ||
          result.receipt
            ?.receipt_number ||
          "receipt created"
        }`,
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Sale could not be completed.",
      );
    }
  }


  const nav = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
    },
    {
      id: "pos",
      label: "Point of Sale",
      icon: ShoppingCart,
    },
    {
      id: "products",
      label: "Products",
      icon: Package,
    },
    {
      id: "customers",
      label: "Customers",
      icon: Users,
    },
    {
      id: "suppliers",
      label: "Suppliers",
      icon: Truck,
    },
    {
      id: "stock",
      label: "Inventory",
      icon: Boxes,
    },
    {
      id: "cash",
      label: "Cash Register",
      icon: WalletCards,
    },
    {
      id: "reports",
      label: "Reports",
      icon: BarChart3,
    },
    {
      id: "settings",
      label: "Settings",
      icon: Settings,
    },
  ];


  const current =
    nav.find(
      (item) =>
        item.id === page,
    ) || nav[0];


  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            GS
          </div>

          <div>
            <div className="brand-name">
              General Store
            </div>

            <div className="brand-subtitle">
              Professional POS
            </div>
          </div>
        </div>

        <nav className="nav">
          {nav.map((item) => {
            const Icon =
              item.icon;

            return (
              <button
                key={item.id}
                className={
                  page === item.id
                    ? "active"
                    : ""
                }
                onClick={() =>
                  setPage(item.id)
                }
              >
                <Icon size={17} />

                <span>
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="user-card">
            <div className="user-name">
              {user.full_name}
            </div>

            <div className="user-role">
              {user.role}
            </div>

            <button
              className="logout"
              onClick={onLogout}
            >
              <LogOut
                size={14}
                style={{
                  verticalAlign:
                    "middle",
                  marginRight: 6,
                }}
              />

              Logout
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="page-title">
              {current.label}
            </div>

            <div className="page-subtitle">
              General Store POS
            </div>
          </div>

          <div className="clock">
            {new Date().toLocaleString(
              "en-PK",
              {
                dateStyle:
                  "medium",
                timeStyle:
                  "short",
              },
            )}
          </div>
        </header>

        <div className="content">
          {page ===
            "dashboard" && (
            <DashboardPage
              dashboard={
                dashboard
              }
              money={money}
            />
          )}

          {page === "pos" && (
            <POSPage
              products={
                filteredProducts
              }
              cart={cart}
              search={search}
              setSearch={
                setSearch
              }
              barcode={barcode}
              setBarcode={
                setBarcode
              }
              barcodeRef={
                barcodeRef
              }
              addToCart={
                addToCart
              }
              updateQuantity={
                updateQuantity
              }
              billDiscount={
                billDiscount
              }
              setBillDiscount={
                setBillDiscount
              }
              paymentMethod={
                paymentMethod
              }
              setPaymentMethod={
                setPaymentMethod
              }
              cashReceived={
                cashReceived
              }
              setCashReceived={
                setCashReceived
              }
              subtotal={
                subtotal
              }
              total={total}
              change={change}
              scanBarcode={
                scanBarcode
              }
              completeSale={
                completeSale
              }
            />
          )}

          {page ===
            "products" && (
            <ProductsPage
              products={
                products
              }
              reload={
                loadProducts
              }
              notify={notify}
            />
          )}

          {page ===
            "customers" && (
            <SimpleDataPage
              title="Customers"
              endpoint="/partners/customers"
              notify={notify}
            />
          )}

          {page ===
            "suppliers" && (
            <SimpleDataPage
              title="Suppliers"
              endpoint="/partners/suppliers"
              notify={notify}
            />
          )}

          {page === "stock" && (
            <StockPage
              notify={notify}
            />
          )}

          {page === "cash" && (
            <CashRegisterPage
              notify={notify}
            />
          )}

          {page ===
            "reports" && (
            <ReportsPage
              money={money}
              notify={notify}
            />
          )}

          {page ===
            "settings" && (
            <SettingsPage
              notify={notify}
            />
          )}
        </div>
      </main>

      {toast && (
        <div className="toast">
          {toast}
        </div>
      )}
    </div>
  );
}


function DashboardPage({
  dashboard,
  money,
}: {
  dashboard:
    | Dashboard
    | null;

  money: (
    value: any,
  ) => string;
}) {
  if (!dashboard) {
    return (
      <div className="empty">
        Loading dashboard...
      </div>
    );
  }

  return (
    <>
      <div className="cards">
        <div className="card">
          <div className="stat-label">
            Today's Sales
          </div>

          <div className="stat-value">
            {money(
              dashboard.sales_total,
            )}
          </div>

          <div className="stat-meta">
            {
              dashboard.sales_count
            }{" "}
            transactions
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Credit / Udhaar
          </div>

          <div className="stat-value">
            {money(
              dashboard.credit_total,
            )}
          </div>

          <div className="stat-meta">
            Outstanding today's
            credit
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Expenses
          </div>

          <div className="stat-value">
            {money(
              dashboard.expense_total,
            )}
          </div>

          <div className="stat-meta">
            Today's expenses
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Low Stock
          </div>

          <div className="stat-value">
            {
              dashboard.low_stock_products
            }
          </div>

          <div className="stat-meta">
            Products needing
            attention
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              Business Overview
            </div>
          </div>

          <div
            style={{
              padding: 18,
              display: "grid",
              gap: 12,
            }}
          >
            <InfoRow
              label="Active Products"
              value={
                dashboard.active_products
              }
            />

            <InfoRow
              label="Transactions Today"
              value={
                dashboard.sales_count
              }
            />

            <InfoRow
              label="Discounts Today"
              value={money(
                dashboard.discount_total,
              )}
            />

            <InfoRow
              label="Today's Sales"
              value={money(
                dashboard.sales_total,
              )}
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div className="panel-title">
              POS Status
            </div>
          </div>

          <div className="empty">
            <Receipt
              size={32}
              style={{
                marginBottom: 10,
              }}
            />

            <div>
              POS ready for sales.
            </div>

            <div
              className="muted"
              style={{
                marginTop: 5,
              }}
            >
              Barcode scanners work
              as keyboard input.
            </div>
          </div>
        </div>
      </div>
    </>
  );
}


function InfoRow({
  label,
  value,
}: {
  label: string;
  value: any;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent:
          "space-between",
        borderBottom:
          "1px solid #27272a",
        paddingBottom: 9,
      }}
    >
      <span className="muted">
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}


function POSPage({
  products,
  cart,
  search,
  setSearch,
  barcode,
  setBarcode,
  barcodeRef,
  addToCart,
  updateQuantity,
  billDiscount,
  setBillDiscount,
  paymentMethod,
  setPaymentMethod,
  cashReceived,
  setCashReceived,
  subtotal,
  total,
  change,
  scanBarcode,
  completeSale,
}: any) {
  return (
    <div className="pos-layout">
      <div className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">
              Products
            </div>

            <div className="muted">
              Search or scan a
              barcode
            </div>
          </div>
        </div>

        <div
          style={{
            padding: 14,
          }}
        >
          <form
            className="search-row"
            onSubmit={
              scanBarcode
            }
          >
            <input
              ref={barcodeRef}
              className="input"
              value={barcode}
              onChange={(event) =>
                setBarcode(
                  event.target
                    .value,
                )
              }
              placeholder="Scan barcode and press Enter..."
              autoComplete="off"
            />

            <button
              className="btn btn-primary"
              type="submit"
            >
              Scan
            </button>
          </form>

          <div
            style={{
              marginTop: 8,
            }}
          >
            <div
              style={{
                position:
                  "relative",
              }}
            >
              <Search
                size={16}
                style={{
                  position:
                    "absolute",
                  left: 11,
                  top: 12,
                  opacity: 0.5,
                }}
              />

              <input
                className="input"
                style={{
                  paddingLeft: 36,
                }}
                value={search}
                onChange={(
                  event,
                ) =>
                  setSearch(
                    event.target
                      .value,
                  )
                }
                placeholder="Search product name or SKU..."
              />
            </div>
          </div>
        </div>

        <div className="product-grid">
          {products.length ===
            0 && (
            <div className="empty">
              No products found.
            </div>
          )}

          {products.map(
            (
              product: Product,
            ) => (
              <button
                className="product-card"
                key={
                  product.id
                }
                onClick={() =>
                  addToCart(
                    product,
                  )
                }
                type="button"
              >
                <div className="product-name">
                  {product.name}
                </div>

                <div className="product-price">
                  {money(
                    product.selling_price,
                  )}
                </div>

                <div className="product-stock">
                  Stock:{" "}
                  {
                    product.stock_quantity
                  }
                </div>
              </button>
            ),
          )}
        </div>
      </div>

      <div className="panel cart">
        <div className="panel-header">
          <div className="panel-title">
            Current Sale
          </div>

          <ShoppingCart
            size={17}
          />
        </div>

        <div className="cart-items">
          {cart.length ===
            0 && (
            <div className="empty">
              <ShoppingCart
                size={30}
                style={{
                  marginBottom: 8,
                }}
              />

              <div>
                Cart is empty
              </div>
            </div>
          )}

          {cart.map(
            (
              item: CartItem,
            ) => (
              <div
                className="cart-item"
                key={
                  item.id
                }
              >
                <div className="cart-item-top">
                  <div>
                    <div className="cart-name">
                      {
                        item.name
                      }
                    </div>

                    <div className="muted">
                      {money(
                        item.selling_price,
                      )}
                    </div>
                  </div>

                  <div className="cart-total">
                    {money(
                      item.quantity *
                        Number(
                          item.selling_price,
                        ) -
                        Number(
                          item.discount ||
                            0,
                        ),
                    )}
                  </div>
                </div>

                <div className="qty-row">
                  <button
                    className="qty-btn"
                    type="button"
                    onClick={() =>
                      updateQuantity(
                        item.id,
                        item.quantity -
                          1,
                      )
                    }
                  >
                    <Minus
                      size={12}
                    />
                  </button>

                  <div className="qty">
                    {
                      item.quantity
                    }
                  </div>

                  <button
                    className="qty-btn"
                    type="button"
                    onClick={() =>
                      updateQuantity(
                        item.id,
                        item.quantity +
                          1,
                      )
                    }
                  >
                    <Plus
                      size={12}
                    />
                  </button>

                  <button
                    className="qty-btn"
                    type="button"
                    style={{
                      marginLeft:
                        "auto",
                    }}
                    onClick={() =>
                      updateQuantity(
                        item.id,
                        0,
                      )
                    }
                  >
                    <Trash2
                      size={12}
                    />
                  </button>
                </div>
              </div>
            ),
          )}
        </div>

        <div className="cart-footer">
          <div className="total-row">
            <span>
              Subtotal
            </span>

            <strong>
              {money(subtotal)}
            </strong>
          </div>

          <div
            style={{
              marginTop: 7,
            }}
          >
            <label className="label">
              Bill Discount
            </label>

            <input
              className="input"
              type="number"
              min="0"
              value={
                billDiscount
              }
              onChange={(
                event,
              ) =>
                setBillDiscount(
                  Number(
                    event.target
                      .value,
                  ) || 0,
                )
              }
            />
          </div>

          <div className="total-row final">
            <span>
              Total
            </span>

            <span>
              {money(total)}
            </span>
          </div>

          <div className="payment-grid">
            {[
              ["cash", "Cash"],
              ["card", "Card"],
              ["bank", "Bank"],
              ["other", "Other"],
            ].map(
              ([
                value,
                label,
              ]) => (
                <button
                  key={value}
                  type="button"
                  className={
                    paymentMethod ===
                    value
                      ? "payment-button active"
                      : "payment-button"
                  }
                  onClick={() =>
                    setPaymentMethod(
                      value,
                    )
                  }
                >
                  {label}
                </button>
              ),
            )}
          </div>

          {paymentMethod ===
            "cash" && (
            <div
              style={{
                marginTop: 9,
              }}
            >
              <label className="label">
                Cash Received
              </label>

              <input
                className="input"
                type="number"
                min="0"
                value={
                  cashReceived
                }
                onChange={(
                  event,
                ) =>
                  setCashReceived(
                    Number(
                      event.target
                        .value,
                    ) || 0,
                  )
                }
              />

              <div
                className="total-row"
                style={{
                  marginTop: 5,
                }}
              >
                <span>
                  Change
                </span>

                <strong>
                  {money(change)}
                </strong>
              </div>
            </div>
          )}

          <button
            className="btn btn-success"
            type="button"
            style={{
              width: "100%",
              marginTop: 12,
              padding: 13,
            }}
            disabled={
              !cart.length
            }
            onClick={
              completeSale
            }
          >
            Complete Sale
          </button>
        </div>
      </div>
    </div>
  );
}


function ProductsPage({
  products,
  reload,
  notify,
}: {
  products: Product[];
  reload: () => Promise<void>;
  notify: (
    message: string,
  ) => void;
}) {
  const [showForm, setShowForm] =
    useState(false);

  const [name, setName] =
    useState("");

  const [sku, setSku] =
    useState("");

  const [sellingPrice, setSellingPrice] =
    useState("");

  const [purchasePrice, setPurchasePrice] =
    useState("");

  const [stock, setStock] =
    useState("0");

  const [saving, setSaving] =
    useState(false);


  async function createProduct(
    event: FormEvent,
  ) {
    event.preventDefault();

    setSaving(true);

    try {
      await api(
        "/products",
        {
          method: "POST",
          body: JSON.stringify({
            name,
            sku:
              sku || null,
            unit: "pcs",
            purchase_price:
              Number(
                purchasePrice,
              ) || 0,
            selling_price:
              Number(
                sellingPrice,
              ) || 0,
            stock_quantity:
              Number(stock) ||
              0,
          }),
        },
      );

      setName("");
      setSku("");
      setSellingPrice(
        "",
      );
      setPurchasePrice(
        "",
      );
      setStock("0");
      setShowForm(false);

      await reload();

      notify(
        "Product created successfully.",
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Product creation failed.",
      );
    } finally {
      setSaving(false);
    }
  }


  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            Product Catalog
          </div>

          <div className="muted">
            {products.length}{" "}
            products
          </div>
        </div>

        <button
          className="btn btn-primary"
          type="button"
          onClick={() =>
            setShowForm(
              !showForm,
            )
          }
        >
          <Plus
            size={14}
            style={{
              verticalAlign:
                "middle",
              marginRight: 5,
            }}
          />

          Add Product
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={
            createProduct
          }
          style={{
            padding: 16,
            borderBottom:
              "1px solid #27272a",
          }}
        >
          <div className="grid grid-3">
            <div>
              <label className="label">
                Product Name
              </label>

              <input
                className="input"
                required
                value={name}
                onChange={(
                  event,
                ) =>
                  setName(
                    event.target
                      .value,
                  )
                }
              />
            </div>

            <div>
              <label className="label">
                SKU
              </label>

              <input
                className="input"
                value={sku}
                onChange={(
                  event,
                ) =>
                  setSku(
                    event.target
                      .value,
                  )
                }
              />
            </div>

            <div>
              <label className="label">
                Purchase Price
              </label>

              <input
                className="input"
                type="number"
                min="0"
                value={
                  purchasePrice
                }
                onChange={(
                  event,
                ) =>
                  setPurchasePrice(
                    event.target
                      .value,
                  )
                }
              />
            </div>

            <div>
              <label className="label">
                Selling Price
              </label>

              <input
                className="input"
                type="number"
                min="0"
                required
                value={
                  sellingPrice
                }
                onChange={(
                  event,
                ) =>
                  setSellingPrice(
                    event.target
                      .value,
                  )
                }
              />
            </div>

            <div>
              <label className="label">
                Opening Stock
              </label>

              <input
                className="input"
                type="number"
                min="0"
                value={stock}
                onChange={(
                  event,
                ) =>
                  setStock(
                    event.target
                      .value,
                  )
                }
              />
            </div>

            <div
              style={{
                display: "flex",
                alignItems:
                  "end",
              }}
            >
              <button
                className="btn btn-primary"
                disabled={
                  saving
                }
                style={{
                  width:
                    "100%",
                }}
              >
                {saving
                  ? "Saving..."
                  : "Save Product"}
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>
                Product
              </th>

              <th>SKU</th>

              <th>
                Purchase
              </th>

              <th>Sale</th>

              <th>Stock</th>

              <th>
                Status
              </th>
            </tr>
          </thead>

          <tbody>
            {products.map(
              (
                product,
              ) => (
                <tr
                  key={
                    product.id
                  }
                >
                  <td>
                    <strong>
                      {
                        product.name
                      }
                    </strong>
                  </td>

                  <td>
                    {product.sku ||
                      "—"}
                  </td>

                  <td>
                    {money(
                      product.purchase_price,
                    )}
                  </td>

                  <td>
                    {money(
                      product.selling_price,
                    )}
                  </td>

                  <td>
                    {
                      product.stock_quantity
                    }
                  </td>

                  <td>
                    <span
                      className={
                        product.stock_quantity <=
                        product.minimum_stock
                          ? "badge badge-yellow"
                          : "badge badge-green"
                      }
                    >
                      {product.stock_quantity <=
                      0
                        ? "Out"
                        : product.stock_quantity <=
                            product.minimum_stock
                          ? "Low"
                          : "OK"}
                    </span>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function SimpleDataPage({
  title,
  endpoint,
  notify,
}: {
  title: string;
  endpoint: string;
  notify: (
    message: string,
  ) => void;
}) {
  const [items, setItems] =
    useState<any[]>([]);

  const [loading, setLoading] =
    useState(true);


  async function load() {
    setLoading(true);

    try {
      const result =
        await api(endpoint);

      setItems(
        Array.isArray(
          result,
        )
          ? result
          : result.items ||
              [],
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : `Could not load ${title}.`,
      );
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    load();
  }, [endpoint]);


  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            {title}
          </div>

          <div className="muted">
            Partner management
            and account
            records
          </div>
        </div>

        <button
          className="btn"
          type="button"
          onClick={load}
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="empty">
          Loading...
        </div>
      ) : items.length ===
        0 ? (
        <div className="empty">
          No records found.
        </div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>
                  Status
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map(
                (item) => (
                  <tr
                    key={
                      item.id
                    }
                  >
                    <td>
                      <strong>
                        {
                          item.name
                        }
                      </strong>
                    </td>

                    <td>
                      {item.phone ||
                        "—"}
                    </td>

                    <td>
                      {item.email ||
                        "—"}
                    </td>

                    <td>
                      <span
                        className={
                          item.active
                            ? "badge badge-green"
                            : "badge badge-red"
                        }
                      >
                        {item.active
                          ? "Active"
                          : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


function StockPage({
  notify,
}: {
  notify: (
    message: string,
  ) => void;
}) {
  const [data, setData] =
    useState<any>(null);


  async function load() {
    try {
      setData(
        await api(
          "/stock/dashboard?limit=200",
        ),
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load inventory.",
      );
    }
  }


  useEffect(() => {
    load();
  }, []);


  if (!data) {
    return (
      <div className="empty">
        Loading inventory...
      </div>
    );
  }


  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            Inventory
          </div>

          <div className="muted">
            Stock health and
            low-stock
            monitoring
          </div>
        </div>

        <button
          className="btn"
          type="button"
          onClick={load}
        >
          Refresh
        </button>
      </div>

      <div className="cards">
        <div className="card">
          <div className="stat-label">
            Total Products
          </div>

          <div className="stat-value">
            {
              data.total_products
            }
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Active Products
          </div>

          <div className="stat-value">
            {
              data.active_products
            }
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Low Stock
          </div>

          <div className="stat-value">
            {
              data.low_stock_products
            }
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Out of Stock
          </div>

          <div className="stat-value">
            {
              data.out_of_stock_products
            }
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>
                Product
              </th>
              <th>SKU</th>
              <th>Stock</th>
              <th>
                Minimum
              </th>
              <th>
                Sale Price
              </th>
              <th>
                Status
              </th>
            </tr>
          </thead>

          <tbody>
            {data.items?.map(
              (item: any) => (
                <tr
                  key={
                    item.product_id
                  }
                >
                  <td>
                    {
                      item.product_name
                    }
                  </td>

                  <td>
                    {item.sku ||
                      "—"}
                  </td>

                  <td>
                    {
                      item.stock_quantity
                    }
                  </td>

                  <td>
                    {
                      item.minimum_stock
                    }
                  </td>

                  <td>
                    {money(
                      item.selling_price,
                    )}
                  </td>

                  <td>
                    <span
                      className={
                        item.out_of_stock
                          ? "badge badge-red"
                          : "badge badge-yellow"
                      }
                    >
                      {item.out_of_stock
                        ? "Out"
                        : "Low"}
                    </span>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function CashRegisterPage({
  notify,
}: {
  notify: (
    message: string,
  ) => void;
}) {
  const [register, setRegister] =
    useState<any>(null);

  const [amount, setAmount] =
    useState("0");

  const [closing, setClosing] =
    useState("0");


  async function load() {
    try {
      const result =
        await api(
          "/inventory/cash-register/current",
        );

      setRegister(
        result,
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load register.",
      );

      setRegister(
        null,
      );
    }
  }


  useEffect(() => {
    load();
  }, []);


  async function openRegister() {
    try {
      await api(
        "/inventory/cash-register/open",
        {
          method: "POST",
          body: JSON.stringify({
            opening_balance:
              Number(amount) ||
              0,
          }),
        },
      );

      notify(
        "Cash register opened.",
      );

      await load();
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not open register.",
      );
    }
  }


  async function closeRegister() {
    try {
      await api(
        "/inventory/cash-register/close",
        {
          method: "POST",
          body: JSON.stringify({
            actual_closing_balance:
              Number(
                closing,
              ) || 0,
          }),
        },
      );

      notify(
        "Cash register closed.",
      );

      await load();
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not close register.",
      );
    }
  }


  return (
    <div className="grid grid-2">
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            Current Register
          </div>
        </div>

        {register ? (
          <div
            style={{
              padding: 18,
            }}
          >
            <InfoRow
              label="Opening Balance"
              value={money(
                register.opening_balance,
              )}
            />

            <InfoRow
              label="Expected Closing"
              value={
                register.expected_closing_balance ===
                null
                  ? "Calculated at close"
                  : money(
                      register.expected_closing_balance,
                    )
              }
            />

            <div
              style={{
                marginTop: 18,
              }}
            >
              <label className="label">
                Actual Closing
                Cash
              </label>

              <input
                className="input"
                type="number"
                min="0"
                value={
                  closing
                }
                onChange={(
                  event,
                ) =>
                  setClosing(
                    event.target
                      .value,
                  )
                }
              />

              <button
                className="btn btn-danger"
                type="button"
                style={{
                  width:
                    "100%",
                  marginTop: 10,
                }}
                onClick={
                  closeRegister
                }
              >
                Close Register
              </button>
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: 18,
            }}
          >
            <div className="muted">
              No register is
              currently open.
            </div>

            <label
              className="label"
              style={{
                marginTop: 15,
              }}
            >
              Opening Cash
            </label>

            <input
              className="input"
              type="number"
              min="0"
              value={amount}
              onChange={(
                event,
              ) =>
                setAmount(
                  event.target
                    .value,
                )
              }
            />

            <button
              className="btn btn-success"
              type="button"
              style={{
                width:
                  "100%",
                marginTop: 10,
              }}
              onClick={
                openRegister
              }
            >
              Open Register
            </button>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            Register
            Information
          </div>
        </div>

        <div className="empty">
          <WalletCards
            size={30}
            style={{
              marginBottom: 8,
            }}
          />

          <div>
            Use the register
            at the beginning
            and end of each
            business day.
          </div>

          <div
            className="muted"
            style={{
              marginTop: 5,
            }}
          >
            Opening and closing
            balances are
            recorded by the
            POS.
          </div>
        </div>
      </div>
    </div>
  );
}


function ReportsPage({
  money,
  notify,
}: {
  money: (
    value: any,
  ) => string;

  notify: (
    message: string,
  ) => void;
}) {
  const [report, setReport] =
    useState<any>(null);

  const [profit, setProfit] =
    useState<any>(null);


  async function load() {
    try {
      const [
        sales,
        profitData,
      ] = await Promise.all([
        api(
          "/reports/sales",
        ),
        api(
          "/reports/profit",
        ),
      ]);

      setReport(sales);
      setProfit(
        profitData,
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load reports.",
      );
    }
  }


  useEffect(() => {
    load();
  }, []);


  return (
    <>
      <div className="cards">
        <div className="card">
          <div className="stat-label">
            Sales
          </div>

          <div className="stat-value">
            {money(
              report?.summary
                ?.total,
            )}
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Cost of Goods
          </div>

          <div className="stat-value">
            {money(
              profit?.cost_of_goods,
            )}
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Gross Profit
          </div>

          <div className="stat-value">
            {money(
              profit?.gross_profit,
            )}
          </div>
        </div>

        <div className="card">
          <div className="stat-label">
            Net Profit
          </div>

          <div className="stat-value">
            {money(
              profit?.net_profit,
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">
              Sales Report
            </div>

            <div className="muted">
              Last 30 days
            </div>
          </div>

          <button
            className="btn"
            type="button"
            onClick={load}
          >
            Refresh
          </button>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>
                  Transactions
                </th>
                <th>Total</th>
              </tr>
            </thead>

            <tbody>
              {report?.daily?.map(
                (row: any) => (
                  <tr
                    key={
                      row.date
                    }
                  >
                    <td>
                      {row.date}
                    </td>

                    <td>
                      {
                        row.count
                      }
                    </td>

                    <td>
                      {money(
                        row.total,
                      )}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}


function SettingsPage({
  notify,
}: {
  notify: (
    message: string,
  ) => void;
}) {
  const [shop, setShop] =
    useState<any>(null);

  const [name, setName] =
    useState("");

  const [receiptWidth, setReceiptWidth] =
    useState(80);

  const [logoLoading, setLogoLoading] =
    useState(false);


  async function load() {
    try {
      const result =
        await api("/shop");

      setShop(result);

      setName(
        result.name || "",
      );

      setReceiptWidth(
        result.receipt_width ||
          80,
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not load settings.",
      );
    }
  }


  useEffect(() => {
    load();
  }, []);


  async function save() {
    try {
      await api(
        "/shop",
        {
          method: "PATCH",
          body: JSON.stringify({
            name,
            receipt_width:
              receiptWidth,
          }),
        },
      );

      notify(
        "Shop settings saved.",
      );

      await load();
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not save settings.",
      );
    }
  }


  async function uploadLogo(
    event: React.ChangeEvent<HTMLInputElement>,
  ) {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    setLogoLoading(true);

    try {
      const token =
        localStorage.getItem(
          "pos_token",
        );

      const formData =
        new FormData();

      formData.append(
        "file",
        file,
      );

      const response =
        await fetch(
          `${API}/shop/logo`,
          {
            method: "POST",
            headers: token
              ? {
                  Authorization:
                    `Bearer ${token}`,
                }
              : {},
            body: formData,
          },
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Logo upload failed.",
        );
      }

      setShop(body);

      notify(
        "Shop logo uploaded.",
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Logo upload failed.",
      );
    } finally {
      setLogoLoading(false);

      event.target.value =
        "";
    }
  }


  async function removeLogo() {
    try {
      const result =
        await api(
          "/shop/logo",
          {
            method: "DELETE",
          },
        );

      setShop(result);

      notify(
        "Shop logo removed.",
      );
    } catch (error) {
      notify(
        error instanceof Error
          ? error.message
          : "Could not remove logo.",
      );
    }
  }


  return (
    <div className="grid grid-2">
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            Shop Settings
          </div>
        </div>

        <div
          style={{
            padding: 18,
          }}
        >
          <div className="form-group">
            <label className="label">
              Shop Name
            </label>

            <input
              className="input"
              value={name}
              onChange={(
                event,
              ) =>
                setName(
                  event.target
                    .value,
                )
              }
            />
          </div>

          <div className="form-group">
            <label className="label">
              Receipt Width
            </label>

            <select
              className="input"
              value={
                receiptWidth
              }
              onChange={(
                event,
              ) =>
                setReceiptWidth(
                  Number(
                    event.target
                      .value,
                  ),
                )
              }
            >
              <option value={58}>
                58mm
              </option>

              <option value={80}>
                80mm
              </option>
            </select>
          </div>

          <button
            className="btn btn-primary"
            type="button"
            onClick={save}
          >
            Save Settings
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            Shop Logo
          </div>
        </div>

        <div
          style={{
            padding: 18,
          }}
        >
          {shop?.has_logo && (
            <div
              style={{
                marginBottom: 15,
              }}
            >
              <img
                src={`${API}/shop/logo`}
                alt="Shop logo"
                style={{
                  maxWidth: 180,
                  maxHeight: 100,
                  objectFit:
                    "contain",
                  borderRadius: 8,
                }}
              />
            </div>
          )}

          <input
            className="input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={
              uploadLogo
            }
            disabled={
              logoLoading
            }
          />

          {shop?.has_logo && (
            <button
              className="btn btn-danger"
              type="button"
              style={{
                marginTop: 10,
              }}
              onClick={
                removeLogo
              }
            >
              Remove Logo
            </button>
          )}

          <div
            className="muted"
            style={{
              marginTop: 10,
            }}
          >
            PNG, JPEG and WEBP
            logos are supported.
          </div>

          <div
            style={{
              marginTop: 20,
              paddingTop: 18,
              borderTop:
                "1px solid #27272a",
            }}
          >
            <Printer
              size={30}
              style={{
                marginBottom: 8,
              }}
            />

            <div>
              Thermal receipt
              printing is
              supported.
            </div>

            <div
              className="muted"
              style={{
                marginTop: 5,
              }}
            >
              Configure 58mm or
              80mm receipt width
              above.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


export default App;
