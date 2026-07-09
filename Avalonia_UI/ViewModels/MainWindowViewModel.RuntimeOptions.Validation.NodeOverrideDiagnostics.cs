using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
        RuntimeOptionsDiagnosticsOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }
}
