// Copy to Clipboard Utility Hook
import { useToast } from '../components/Toast';

export function useCopyToClipboard() {
  const toast = useToast();

  const copyToClipboard = async (text, label = 'Text') => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${label} copied to clipboard!`);
      return true;
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        toast.success(`${label} copied!`);
        return true;
      } catch (err2) {
        toast.error('Failed to copy');
        return false;
      } finally {
        document.body.removeChild(textArea);
      }
    }
  };

  return copyToClipboard;
}
