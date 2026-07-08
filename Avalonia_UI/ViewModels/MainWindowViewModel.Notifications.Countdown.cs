using System;
using System.Threading;
using System.Threading.Tasks;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int NotificationCountdownTickMilliseconds = 16;

    private CancellationTokenSource? _notificationCountdownCancellation;

    private void StartNotificationCountdownIfNeeded(TimeSpan? autoDismissAfter)
    {
        CancelNotificationCountdown();

        if (autoDismissAfter is null ||
            autoDismissAfter.Value <= TimeSpan.Zero ||
            IsNotificationSticky)
        {
            HasNotificationCountdown = false;
            NotificationCountdownProgress = 0;
            return;
        }

        HasNotificationCountdown = true;
        NotificationCountdownProgress = 1;

        _notificationCountdownCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var cancellationToken = _notificationCountdownCancellation.Token;
        var updateCount = NotificationUpdateCount;
        _ = RunNotificationCountdownAsync(
            autoDismissAfter.Value,
            updateCount,
            cancellationToken);
    }

    private void CancelNotificationCountdown()
    {
        _notificationCountdownCancellation?.Cancel();
        _notificationCountdownCancellation?.Dispose();
        _notificationCountdownCancellation = null;
    }

    private async Task RunNotificationCountdownAsync(
        TimeSpan duration,
        int updateCount,
        CancellationToken cancellationToken)
    {
        var startedAt = DateTimeOffset.Now;

        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var elapsed = DateTimeOffset.Now - startedAt;
                var remainingRatio =
                    1 - elapsed.TotalMilliseconds / duration.TotalMilliseconds;
                NotificationCountdownProgress = Math.Clamp(remainingRatio, 0, 1);

                if (NotificationCountdownProgress <= 0)
                {
                    break;
                }

                var remainingMilliseconds =
                    duration.TotalMilliseconds - elapsed.TotalMilliseconds;
                var delayMilliseconds = Math.Min(
                    NotificationCountdownTickMilliseconds,
                    Math.Max(1, remainingMilliseconds));
                await Task.Delay(
                    TimeSpan.FromMilliseconds(delayMilliseconds),
                    cancellationToken);
            }

            if (!cancellationToken.IsCancellationRequested &&
                IsNotificationOpen &&
                NotificationUpdateCount == updateCount)
            {
                CloseNotification();
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
    }
}
