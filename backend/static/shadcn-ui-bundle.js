/**
 * Minimal shadcn/ui bundle for iframe component rendering.
 * Provides basic component placeholders. Full bundle can be built from frontend.
 */
(function (global) {
  var React = global.React;
  if (!React && typeof window !== "undefined") React = window.React;
  if (!React) {
    console.warn("ShadcnUI: React not found, skipping");
    return;
  }

  var createElement = React.createElement;

  var Card = function (props) {
    return createElement("div", { className: "rounded-lg border bg-card text-card-foreground shadow-sm " + (props.className || "") }, props.children);
  };
  var CardHeader = function (props) {
    return createElement("div", { className: "flex flex-col space-y-1.5 p-6 " + (props.className || "") }, props.children);
  };
  var CardTitle = function (props) {
    return createElement("h3", { className: "text-2xl font-semibold leading-none tracking-tight " + (props.className || "") }, props.children);
  };
  var CardDescription = function (props) {
    return createElement("p", { className: "text-sm text-muted-foreground " + (props.className || "") }, props.children);
  };
  var CardContent = function (props) {
    return createElement("div", { className: "p-6 pt-0 " + (props.className || "") }, props.children);
  };
  var CardFooter = function (props) {
    return createElement("div", { className: "flex items-center p-6 pt-0 " + (props.className || "") }, props.children);
  };
  var Badge = function (props) {
    var v = props.variant || "default";
    var c = v === "secondary" ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground";
    return createElement("span", { className: "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold " + c + " " + (props.className || "") }, props.children);
  };
  var Input = function (props) {
    return createElement("input", Object.assign({}, props, { className: "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm " + (props.className || "") }));
  };
  var Table = function (props) {
    return createElement("table", { className: "w-full caption-bottom text-sm " + (props.className || "") }, props.children);
  };
  var TableHeader = function (props) {
    return createElement("thead", props, props.children);
  };
  var TableBody = function (props) {
    return createElement("tbody", props, props.children);
  };
  var TableRow = function (props) {
    return createElement("tr", Object.assign({}, props, { className: "border-b transition-colors " + (props.className || "") }), props.children);
  };
  var TableHead = function (props) {
    return createElement("th", Object.assign({}, props, { className: "h-12 px-4 text-left align-middle font-medium " + (props.className || "") }), props.children);
  };
  var TableCell = function (props) {
    return createElement("td", Object.assign({}, props, { className: "p-4 align-middle " + (props.className || "") }), props.children);
  };
  var ScrollArea = function (props) {
    return createElement("div", Object.assign({}, props, { className: "overflow-auto " + (props.className || "") }), props.children);
  };

  global.ShadcnUI = {
    Card: Card,
    CardHeader: CardHeader,
    CardTitle: CardTitle,
    CardDescription: CardDescription,
    CardContent: CardContent,
    CardFooter: CardFooter,
    Badge: Badge,
    Input: Input,
    Table: Table,
    TableHeader: TableHeader,
    TableBody: TableBody,
    TableRow: TableRow,
    TableHead: TableHead,
    TableCell: TableCell,
    ScrollArea: ScrollArea,
  };
})(typeof window !== "undefined" ? window : this);
