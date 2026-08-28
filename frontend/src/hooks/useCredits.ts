import { useCallback, useEffect, useState } from "react";
import {
  fetchCreditBalance,
  claimBonus as apiClaimBonus,
} from "../api/credits";

export interface CreditState {
  balance: number | null;
  bonusEligible: boolean;
  nextBonusAt: string | null;
  isAdmin: boolean;
  monthlyGrantAvailable: boolean;
  monthlyGrantAmount: number;
  loading: boolean;
  refetch: () => void;
  claimBonus: () => Promise<void>;
}

export function useCredits(): CreditState {
  const [balance, setBalance] = useState<number | null>(null);
  const [bonusEligible, setBonusEligible] = useState(false);
  const [nextBonusAt, setNextBonusAt] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [monthlyGrantAvailable, setMonthlyGrantAvailable] = useState(false);
  const [monthlyGrantAmount, setMonthlyGrantAmount] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchBalance = useCallback(async () => {
    setLoading(true);
    const res = await fetchCreditBalance();
    if (res.data) {
      setBalance(res.data.balance);
      setBonusEligible(res.data.bonus_eligible);
      setNextBonusAt(res.data.next_bonus_at);
      setIsAdmin(res.data.is_admin);
      setMonthlyGrantAvailable(res.data.monthly_grant_available ?? false);
      setMonthlyGrantAmount(res.data.monthly_grant_amount ?? 0);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  const claimBonus = useCallback(async () => {
    const res = await apiClaimBonus();
    if (res.data) {
      setBalance(res.data.balance);
      setBonusEligible(false);
    }
  }, []);

  return {
    balance,
    bonusEligible,
    nextBonusAt,
    isAdmin,
    monthlyGrantAvailable,
    monthlyGrantAmount,
    loading,
    refetch: fetchBalance,
    claimBonus,
  };
}
