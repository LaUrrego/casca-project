import React, { useState } from 'react';
import logo from './casca_logo.png'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  AlertCircle,
  RefreshCw,
  Upload,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface Transaction {
  check_no: string;
  date: string;
  description: string;
  amount: string;
  category: string;
  image_file?: string;
  is_unusual?: boolean;
}

interface StatementData {
  summary: {
    total_income: number;
    total_expenses: number;
    net_change: number;
    largest_expense: {
      amount: number;
      description: string;
      date: string;
    };
    largest_income: {
      amount: number;
      description: string;
      date: string;
    };
  };
  all_transactions: Transaction[];
  currency: string;
  category_breakdown: {
    [key: string]: number;
  };
  statement_info: {
    opening_balance: number;
    closing_balance: number;
  };
  unusual_transactions: Transaction[];
}

const BankStatementApp: React.FC = () => {
  const [data, setData] = useState<StatementData | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [trainMessage, setTrainMessage] = useState<string | null>(null);

  // Get currency symbol
  const getCurrencySymbol = (currency: string) => {
    const symbols: { [key: string]: string } = {
      USD: '$',
      EUR: '€',
      GBP: '£',
      JPY: '¥',
    };
    return symbols[currency] || currency;
  };

  const formatAmount = (amount: number, currency: string) => {
    const symbol = getCurrencySymbol(currency);
    return `${symbol}${Math.abs(amount).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  // Handler for processing statements 
  const handleSubmit = async () => {
    if (!selectedFile) return;
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('http://127.0.0.1:8000/process-statement', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Reset app to try again
  const resetAnalysis = () => {
    setData(null);
    setSelectedFile(null);
    setTrainMessage(null);
    setShowReviewModal(false);
    setSelectedTransaction(null);
  };

  // Handler to click table rows and update transactions
  const handleTransactionClick = (transaction: Transaction) => {
    setSelectedTransaction(transaction);
    setTrainMessage(null);
    setShowReviewModal(true);
  };

  // Submit handler for updating transactions to train the ML model via updated csv
  const handleTransactionUpdate = async () => {
    if (!selectedTransaction || !data) return;

    try {
      const response = await fetch('http://127.0.0.1:8000/update-transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction: selectedTransaction }),
      });
      if (response.ok) {
        const { message } = await response.json();

        // Update local state
        setData((prev) => {
          if (!prev) return prev;

          // Find the old transaction
          const oldTransaction = prev.all_transactions.find(
            (t) => t.check_no === selectedTransaction.check_no
          );
          const oldCategory = oldTransaction?.category || '';
          const oldAmount = oldTransaction ? parseFloat(oldTransaction.amount) : 0;
          const newCategory = selectedTransaction.category;
          const newAmount = parseFloat(selectedTransaction.amount);

          // Update the all_transactions array
          const updatedAll = prev.all_transactions.map((t) =>
            t.check_no === selectedTransaction.check_no ? selectedTransaction : t
          );

          // Update category breakdown
          const updatedBreakdown = { ...prev.category_breakdown };

          // Subtract from old category total
          if (updatedBreakdown[oldCategory] !== undefined) {
            updatedBreakdown[oldCategory] -= oldAmount;
          }
          // Add to the new category
          if (updatedBreakdown[newCategory] !== undefined) {
            updatedBreakdown[newCategory] += newAmount;
          } else {
            // If user typed a new category not in breakdown
            updatedBreakdown[newCategory] = newAmount;
          }

          // Return the updated state
          return {
            ...prev,
            all_transactions: updatedAll,
            category_breakdown: updatedBreakdown,
          };
        });

        // Show the "model trained!" message
        setTrainMessage(message || 'Model trained!');
      }
    } catch (error) {
      console.error('Error updating transaction:', error);
    }
  };

  const pieColors = [
    '#f97316', 
    '#14b8a6', 
    '#e11d48', 
    '#eab308', 
    '#6366f1', 
    '#10b981', 
    '#ec4899',
    '#3b82f6', 
  ];

  return (
    <div
      className="min-h-screen bg-white p-8 transition-colors ease-in-out duration-300"
      style={{ fontFamily: 'Inter, sans-serif' }}
    >
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex flex-col items-center md:items-start gap-2">
          <img
            src={logo}
            alt="Company Logo"
            className="h-16 w-auto object-contain"
          />
          <h1 className="text-2xl font-bold tracking-tight text-gray-800">
            Bank Statement Analysis - MVP
          </h1>
        </div>

        {data && (
          <div className="flex flex-col md:items-end gap-2 w-full md:w-auto">
            {/* Currency and "New Analysis" */}
            <div className="flex items-center gap-4">
              <span className="text-lg font-semibold text-gray-700">
                {data.currency || 'USD'}
              </span>
              <Button
                variant="outline"
                onClick={resetAnalysis}
                className="flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                New Analysis
              </Button>
            </div>

            {/* Red indicator for how many to_review */}
            {data.all_transactions && (() => {
              // Filter by category === 'to_review'
              const toReviewCount = data.all_transactions.filter(
                (t) => t.category === 'to_review'
              ).length;

              return (
                toReviewCount > 0 && (
                  <div className="flex items-center mt-1 gap-2 text-sm text-red-600 font-semibold">
                    <AlertCircle className="h-4 w-4" />
                    <span>
                      {toReviewCount} transaction
                      {toReviewCount > 1 ? 's' : ''} need review
                    </span>
                  </div>
                )
              );
            })()}
          </div>
        )}
      </div>

      {/* File Upload if no data */}
      {!data && (
        <Card className="w-full mb-8 border border-gray-200 hover:shadow-md transition-shadow">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
              <Upload className="h-12 w-12 text-gray-400 mb-4" />
              <label className="cursor-pointer mb-4">
                <span className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 transition-colors">
                  Choose PDF File
                </span>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
              {selectedFile && (
                <div className="flex flex-col items-center gap-2">
                  <span className="text-sm text-gray-600">{selectedFile.name}</span>
                  <Button
                    onClick={handleSubmit}
                    disabled={isLoading}
                    className="hover:shadow-lg transition-all"
                  >
                    {isLoading ? 'Processing...' : 'Analyze Statement'}
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {/* Income */}
            <Card className="border border-gray-200 transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="text-lg">Total Income</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-green-700">
                  {formatAmount(data.summary.total_income, data.currency)}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Largest:{' '}
                  {formatAmount(data.summary.largest_income.amount, data.currency)}
                </p>
              </CardContent>
            </Card>

            {/* Net Change */}
            <Card className="border border-gray-200 transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="text-lg">Net Change</CardTitle>
              </CardHeader>
              <CardContent>
                <p
                  className={`text-2xl font-bold ${
                    data.summary.net_change >= 0 ? 'text-green-700' : 'text-red-700'
                  }`}
                >
                  {formatAmount(data.summary.net_change, data.currency)}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Opening:{' '}
                  {formatAmount(data.statement_info.opening_balance, data.currency)}
                </p>
              </CardContent>
            </Card>

            {/* Expenses */}
            <Card className="border border-gray-200 transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="text-lg">Total Expenses</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-red-700">
                  {formatAmount(data.summary.total_expenses, data.currency)}
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Largest:{' '}
                  {formatAmount(Math.abs(data.summary.largest_expense.amount), data.currency)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabs for different views */}
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="mb-2">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="categories">Categories</TabsTrigger>
              <TabsTrigger value="transactions">Transactions</TabsTrigger>
              <TabsTrigger value="unusual">Unusual Activity</TabsTrigger>
            </TabsList>

            {/* OVERVIEW TAB */}
            <TabsContent value="overview">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Transaction History */}
                <Card className="border border-gray-200 hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <CardTitle>Transaction History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={data.all_transactions.map((t) => ({
                            date: t.date,
                            amount: parseFloat(t.amount),
                          }))}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip
                            formatter={(value: number) => [
                              formatAmount(value, data.currency),
                              'Amount',
                            ]}
                          />
                          <Line
                            type="monotone"
                            dataKey="amount"
                            stroke="#2563eb"
                            strokeWidth={2}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                {/* Category Pie Chart */}
                <Card className="border border-gray-200 hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <CardTitle>Category Distribution</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={Object.entries(data.category_breakdown)
                              .filter(([_, amt]) => Math.abs(amt) > 0)
                              .map(([category, amt]) => ({
                                name: category,
                                value: Math.abs(amt),
                              }))
                              .sort((a, b) => b.value - a.value)
                              .slice(0, 6)}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={80}
                            label={({ name, percent }) =>
                              `${name} (${(percent * 100).toFixed(0)}%)`
                            }
                          >
                            {Object.keys(data.category_breakdown).map((_, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={pieColors[index % pieColors.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value: number) =>
                              formatAmount(value, data.currency)
                            }
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* CATEGORIES TAB */}
            <TabsContent value="categories">
              <Card className="border border-gray-200 hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle>Category Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">% of Total</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {Object.entries(data.category_breakdown).map(([category, amt]) => (
                        <TableRow key={category}>
                          <TableCell className="font-medium">
                            {category.replace('_', ' ')}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatAmount(amt, data.currency)}
                          </TableCell>
                          <TableCell className="text-right">
                            {(
                              (Math.abs(amt) /
                                (data.summary.total_income +
                                  Math.abs(data.summary.total_expenses))) *
                              100
                            ).toFixed(1)}
                            %
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* TRANSACTIONS TAB */}
            <TabsContent value="transactions">
              <Card className="border border-gray-200 hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle>All Transactions</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.all_transactions.map((transaction, index) => (
                        <TableRow
                          key={index}
                          className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                            transaction.category === 'to_review'
                              ? 'bg-yellow-50'
                              : ''
                          }`}
                          onClick={() => handleTransactionClick(transaction)}
                        >
                          <TableCell>{transaction.date}</TableCell>
                          <TableCell>
                            {transaction.description || 'N/A'}
                          </TableCell>
                          <TableCell>
                            {transaction.category.replace('_', ' ')}
                          </TableCell>
                          <TableCell
                            className={`text-right ${
                              parseFloat(transaction.amount) >= 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            }`}
                          >
                            {formatAmount(parseFloat(transaction.amount), data.currency)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            {/* UNUSUAL TAB */}
            <TabsContent value="unusual">
              <Card className="border border-gray-200 hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle>Unusual Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.unusual_transactions.map((transaction, index) => (
                        <TableRow
                          key={index}
                          className={`cursor-pointer hover:bg-gray-50 transition-colors ${
                            transaction.category === 'to_review'
                              ? 'bg-yellow-50'
                              : ''
                          }`}
                          onClick={() => handleTransactionClick(transaction)}
                        >
                          <TableCell>{transaction.date}</TableCell>
                          <TableCell>{transaction.description || 'N/A'}</TableCell>
                          <TableCell>
                            {transaction.category.replace('_', ' ')}
                          </TableCell>
                          <TableCell
                            className={`text-right ${
                              parseFloat(transaction.amount) >= 0
                                ? 'text-green-600'
                                : 'text-red-600'
                            }`}
                          >
                            {formatAmount(parseFloat(transaction.amount), data.currency)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* REVIEW MODAL */}
          <Dialog open={showReviewModal} onOpenChange={setShowReviewModal}>
            <DialogContent
              aria-describedby="review-transaction-description"
              className="w-[90%] sm:max-w-2xl p-6 max-h-[100vh] overflow-y-auto scale-[0.97]"
            >
              <DialogHeader className='mb-4'>
                <DialogTitle>Review Transaction</DialogTitle>
                <DialogDescription id="review-transaction-description">
                  Please review and update details, then click “Update Transaction” to retrain.
                </DialogDescription>
              </DialogHeader>

              {trainMessage ? (
                /* If the model was trained, show success message */
                <div className="py-4">
                  <h2 className="text-xl font-semibold text-green-600 mb-2">
                    {trainMessage}
                  </h2>
                  <p className="text-sm text-gray-700 mb-4">
                    Your changes have been submitted and the model has been updated.
                  </p>
                  <div className="flex justify-end">
                    <Button
                      onClick={() => {
                        setShowReviewModal(false);
                        setTrainMessage(null);
                      }}
                    >
                      Close
                    </Button>
                  </div>
                </div>
              ) : (
                /* Otherwise show the transaction form */
                <div className="space-y-4">
                  {selectedTransaction?.image_file && (
                    <div className="mb-4 flex justify-center">
                      <img
                        src={
                          selectedTransaction.image_file
                            ? `http://127.0.0.1:8000/${selectedTransaction.image_file}`
                            : ''
                        }
                        alt="Check"
                        className="max-w-full rounded-lg shadow-lg"
                      />
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium">Date</label>
                      <Input
                        value={selectedTransaction?.date || ''}
                        disabled
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Check Number</label>
                      <Input
                        value={selectedTransaction?.check_no || ''}
                        disabled
                        className="mt-1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Description</label>
                    <Input
                      value={selectedTransaction?.description || ''}
                      onChange={(e) =>
                        setSelectedTransaction((prev) =>
                          prev ? { ...prev, description: e.target.value } : null
                        )
                      }
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium">Amount</label>
                    <Input
                      type="number"
                      value={selectedTransaction?.amount || ''}
                      onChange={(e) =>
                        setSelectedTransaction((prev) =>
                          prev ? { ...prev, amount: e.target.value } : null
                        )
                      }
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <label className="text-sm font-medium">Category</label>
                    <Select
                      value={selectedTransaction?.category || ''}
                      onValueChange={(value) =>
                        setSelectedTransaction((prev) =>
                          prev ? { ...prev, category: value } : null
                        )
                      }
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[600px] overflow-y-auto">
                        {Object.keys(data.category_breakdown).map((category) => (
                          <SelectItem key={category} value={category}>
                            {category.replace('_', ' ')}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex justify-end gap-4 pt-4">
                    <Button variant="outline" onClick={() => setShowReviewModal(false)}>
                      Cancel
                    </Button>
                    <Button
                      className="bg-blue-600 hover:bg-blue-700 text-white transition-colors"
                      onClick={handleTransactionUpdate}
                    >
                      Update Transaction
                    </Button>
                  </div>
                </div>
              )}
            </DialogContent>
          </Dialog>
        </>
      )}
    </div>
  );
};

export default BankStatementApp;
