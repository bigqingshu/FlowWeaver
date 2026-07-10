using System;
using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record DataPreviewStateSelectionCandidate(
    string StateKey,
    IReadOnlyList<string> TableRefIds);

public sealed record DataPreviewSelectionResolution(
    string? StateKey,
    string? TableRefId);

public sealed class DataPreviewSelectionState
{
    private string? preferredStateKey;
    private string? preferredTableRefId;

    public void Capture(string? stateKey, string? tableRefId)
    {
        preferredStateKey = stateKey;
        preferredTableRefId = tableRefId;
    }

    public DataPreviewSelectionResolution Resolve(
        IReadOnlyList<DataPreviewStateSelectionCandidate> candidates)
    {
        var selectedState = FindByStateKey(candidates)
            ?? FindByTableRefId(candidates)
            ?? FindFirstReadableState(candidates)
            ?? (candidates.Count > 0 ? candidates[0] : null);
        if (selectedState is null)
        {
            return new DataPreviewSelectionResolution(null, null);
        }

        var selectedTableRefId = FindPreferredTableRefId(selectedState)
            ?? (selectedState.TableRefIds.Count > 0
                ? selectedState.TableRefIds[0]
                : null);
        return new DataPreviewSelectionResolution(
            selectedState.StateKey,
            selectedTableRefId);
    }

    private static DataPreviewStateSelectionCandidate? FindFirstReadableState(
        IReadOnlyList<DataPreviewStateSelectionCandidate> candidates)
    {
        foreach (var candidate in candidates)
        {
            if (candidate.TableRefIds.Count > 0)
            {
                return candidate;
            }
        }

        return null;
    }

    private DataPreviewStateSelectionCandidate? FindByStateKey(
        IReadOnlyList<DataPreviewStateSelectionCandidate> candidates)
    {
        if (string.IsNullOrWhiteSpace(preferredStateKey))
        {
            return null;
        }

        foreach (var candidate in candidates)
        {
            if (string.Equals(
                    candidate.StateKey,
                    preferredStateKey,
                    StringComparison.Ordinal))
            {
                return candidate;
            }
        }

        return null;
    }

    private DataPreviewStateSelectionCandidate? FindByTableRefId(
        IReadOnlyList<DataPreviewStateSelectionCandidate> candidates)
    {
        if (string.IsNullOrWhiteSpace(preferredTableRefId))
        {
            return null;
        }

        foreach (var candidate in candidates)
        {
            if (ContainsTableRefId(candidate, preferredTableRefId))
            {
                return candidate;
            }
        }

        return null;
    }

    private string? FindPreferredTableRefId(
        DataPreviewStateSelectionCandidate candidate)
    {
        return !string.IsNullOrWhiteSpace(preferredTableRefId)
            && ContainsTableRefId(candidate, preferredTableRefId)
                ? preferredTableRefId
                : null;
    }

    private static bool ContainsTableRefId(
        DataPreviewStateSelectionCandidate candidate,
        string tableRefId)
    {
        foreach (var candidateTableRefId in candidate.TableRefIds)
        {
            if (string.Equals(
                    candidateTableRefId,
                    tableRefId,
                    StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }
}
